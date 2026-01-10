#!/usr/bin/env python3
"""
每日任务入口脚本

支持分步执行或一键执行全部任务。
所有任务均为异步执行，使用 asyncio.run() 作为入口点。

Usage:
    python scripts/daily_crawl.py --task arxiv     # arXiv 获取
    python scripts/daily_crawl.py --task rss       # RSS 获取
    python scripts/daily_crawl.py --task analyze   # 浅度分析
    python scripts/daily_crawl.py --task summary   # 生成日报
    python scripts/daily_crawl.py --task notify    # 发送通知
    python scripts/daily_crawl.py --task all       # 全部执行

Exit codes:
    0: 成功（包括无新论文但其他任务正常完成）
    1: 配置错误
    3: 执行错误
"""

import argparse
import asyncio
import os
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, TypeVar

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pydantic import BaseModel

from src.config import get_settings, check_first_run, check_required_config
from src.data_fetchers.arxiv import AsyncArxivClient
from src.data_fetchers.status import DedupStatus
from src.data_fetchers.ids_tracker import get_analyzed_tracker, get_fetched_tracker
from src.data_fetchers.news import NewsFetcher
from src.agents.paper import PaperLightAnalyzer
from src.agents.news import NewsLightAnalyzer
from src.generators import DailyReportGenerator
from src.llm import LLMClient
from src.models import Paper, NewsItem, AnalyzedPaper, AnalyzedNews
from src.notifiers.feishu import get_notifier
from src.file_index import write_file_list


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# 数据目录
DATA_DIR = project_root / "data"
PAPERS_DIR = DATA_DIR / "papers"
NEWS_DIR = DATA_DIR / "news"
REPORTS_DIR = DATA_DIR / "reports"


def get_today_date() -> str:
    """获取今天的日期字符串 YYYY-MM-DD"""
    return datetime.now().strftime("%Y-%m-%d")

TModel = TypeVar("TModel", bound=BaseModel)

def _resolve_compat_json_path(file_path: Path) -> Path:
    """
    兼容 .json / .jsonl：
    - 若目标文件不存在，尝试寻找另一种后缀
    - 若 suffix 为 .jsonl，保存时统一写入 .json
    """
    if file_path.exists():
        return file_path
    if file_path.suffix == ".json":
        alt_path = file_path.with_suffix(".jsonl")
    else:
        alt_path = file_path.with_suffix(".json")
    return alt_path if alt_path.exists() else file_path


def load_models_json(file_path: Path, model: type[TModel]) -> list[TModel]:
    """从 JSON/JSONL 文件加载模型列表；文件不存在则返回空列表。"""
    file_path = _resolve_compat_json_path(file_path)
    if not file_path.exists():
        return []

    items: list[TModel] = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix == ".jsonl":
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    items.append(model.model_validate_json(line))
            else:
                data = json.load(f)
                if not isinstance(data, list):
                    logger.warning(f"JSON 结构不是 list，跳过: {file_path}")
                    return []
                for obj in data:
                    items.append(model.model_validate(obj))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"读取/解析失败: {file_path}: {e}")
        return []

    return items


def save_models_json(models: list[BaseModel], file_path: Path, *, log_label: str) -> None:
    """保存模型列表到 JSON 文件（统一写入 .json）。"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if file_path.suffix == ".jsonl":
        file_path = file_path.with_suffix(".json")

    with open(file_path, "w", encoding="utf-8") as f:
        data = [json.loads(m.model_dump_json()) for m in models]
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"保存 {len(models)} 条{log_label}到 {file_path}")


def merge_papers_by_id_keep_success(
    existing: list[AnalyzedPaper],
    incoming: list[Paper],
    ) -> list[AnalyzedPaper]:
    """按论文 id 合并：已 success 的旧记录完全保留；否则用新抓取基础字段更新，保留分析字段。"""
    by_id: dict[str, AnalyzedPaper] = {p.id: p for p in existing}

    for p in incoming:
        old = by_id.get(p.id)
        if old and old.analysis_status == "success":
            continue

        if old:
            by_id[p.id] = AnalyzedPaper(
                **p.model_dump(),
                light_analysis=old.light_analysis,
                analyzed_at=old.analyzed_at,
                analysis_status=old.analysis_status,
                analysis_error=old.analysis_error,
            )
        else:
            by_id[p.id] = AnalyzedPaper(**p.model_dump(), analysis_status="pending")

    # 稳定排序：发布时间降序（无 published 的放最后）
    return sorted(
        by_id.values(),
        key=lambda x: x.published.timestamp() if x.published else 0,
        reverse=True,
    )


def merge_news_by_id_keep_success(
    existing: list[AnalyzedNews],
    incoming: list[NewsItem],
    ) -> list[AnalyzedNews]:
    """按新闻 id 合并：已 success 的旧记录完全保留；否则用新抓取基础字段更新，保留分析字段。"""
    by_id: dict[str, AnalyzedNews] = {n.id: n for n in existing}

    for item in incoming:
        old = by_id.get(item.id)
        if old and old.analysis_status == "success":
            continue

        if old:
            by_id[item.id] = AnalyzedNews(
                **item.model_dump(),
                light_analysis=old.light_analysis,
                analyzed_at=old.analyzed_at,
                analysis_status=old.analysis_status,
                analysis_error=old.analysis_error,
            )
        else:
            by_id[item.id] = AnalyzedNews(**item.model_dump(), analysis_status="pending")

    return sorted(
        by_id.values(),
        key=lambda x: x.published.timestamp() if x.published else 0,
        reverse=True,
    )


async def task_arxiv() -> int:
    """
    任务：获取 arXiv 论文并去重

    使用 fetched_ids.json 进行历史去重，支持30天自动清理。
    默认获取过去25小时内发布的论文。

    Returns:
        状态码: 0=有新内容, 1=无新内容, 2=错误
    """
    logger.info("=" * 50)
    logger.info("开始执行任务: arXiv 获取")
    logger.info("=" * 50)

    settings = get_settings()
    categories = settings.arxiv.categories
    max_results = settings.arxiv.max_results
    max_pages = getattr(settings.arxiv, "max_pages", 20)

    logger.info(f"目标分类: {categories}")
    logger.info(f"每页最大结果数: {max_results}")
    logger.info(f"每分类最多分页次数: {max_pages}")

    # 初始化 ProcessedTracker 并清理过期记录
    tracker = get_fetched_tracker(DATA_DIR / "fetched_ids.json")
    cleaned = tracker.cleanup()
    if cleaned > 0:
        logger.info(f"清理过期记录: {cleaned} 条")

    # 获取论文（默认25小时，可通过环境变量 ARXIV_HOURS 调整）
    client = AsyncArxivClient(
        max_results_per_category=max_results,
        max_pages_per_category=max_pages,
        delay_between_requests=settings.arxiv.request_delay,
        timeout=settings.arxiv.timeout,
    )
    hours = int(os.environ.get("ARXIV_HOURS", "25"))
    papers = await client.fetch_recent_papers(categories, hours=hours)
    logger.info(f"获取到 {len(papers)} 篇论文（过去 {hours} 小时）")

    # 使用 fetched_ids.json 去重
    fetched_ids = tracker.get_paper_ids()
    new_papers = [p for p in papers if p.id not in fetched_ids]
    duplicates_count = len(papers) - len(new_papers)

    logger.info(
        f"去重完成: 获取 {len(papers)} 篇, "
        f"历史重复 {duplicates_count} 篇, "
        f"新论文 {len(new_papers)} 篇"
    )

    if not new_papers:
        return DedupStatus.NO_NEW_CONTENT

    # 保存新论文（同日多次运行：按 id 合并追加，避免覆盖旧数据/已分析结果）
    today = get_today_date()
    file_path = PAPERS_DIR / f"{today}.json"
    existing = load_models_json(file_path, AnalyzedPaper)
    merged = merge_papers_by_id_keep_success(existing, new_papers)
    save_models_json(merged, file_path, log_label="论文")

    # 标记为已处理
    tracker.mark_papers([p.id for p in new_papers])

    logger.info(f"arXiv 任务完成: {len(new_papers)} 篇新论文")
    return DedupStatus.HAS_NEW_CONTENT


async def task_rss() -> list[NewsItem]:
    """
    任务：获取新闻热点（RSS + Crawler）

    使用 NewsFetcher 统一获取 RSS 和 Crawler 两种类型的新闻源。
    NewsFetcher 内部已实现时间过滤、历史去重和排序。

    Returns:
        热点列表
    """
    logger.info("=" * 50)
    logger.info("开始执行任务: 新闻获取")
    logger.info("=" * 50)

    # 使用 NewsFetcher 获取新闻（内置时间过滤、历史去重、排序）
    # 新闻保持较长的时间窗口（168小时 = 7天）
    fetcher = NewsFetcher()
    news = await fetcher.fetch_all(hours=168)

    if not news:
        logger.warning("未获取到任何新闻")
        return []

    # 保存热点（同日多次运行：按 id 合并追加，避免覆盖旧数据/已分析结果）
    today = get_today_date()
    file_path = NEWS_DIR / f"{today}.json"
    existing = load_models_json(file_path, AnalyzedNews)
    merged = merge_news_by_id_keep_success(existing, news)
    save_models_json(merged, file_path, log_label="热点")

    # 标记为已处理
    tracker = get_fetched_tracker(DATA_DIR / "fetched_ids.json")
    tracker.mark_news([item.id for item in news])

    logger.info(f"新闻任务完成: {len(news)} 条热点")
    return news


async def task_analyze() -> tuple[list[AnalyzedPaper], list[AnalyzedNews]]:
    """
    任务：浅度分析（论文 + 热点并行）

    支持增量分析：只分析未成功的数据，已成功的数据直接复用。
    这样可以避免重复调用 LLM API，节省费用，支持断点续传。

    Returns:
        (分析后的论文列表, 分析后的热点列表)
    """
    logger.info("=" * 50)
    logger.info("开始执行任务: 浅度分析")
    logger.info("=" * 50)

    today = get_today_date()
    papers_file = PAPERS_DIR / f"{today}.json"
    news_file = NEWS_DIR / f"{today}.json"

    # 加载今日数据（统一以 Analyzed schema 读取：可兼容 raw Paper/NewsItem，且能保留分析状态）
    existing_papers = load_models_json(papers_file, AnalyzedPaper)
    existing_news = load_models_json(news_file, AnalyzedNews)

    # 仅以 analyzed_ids.json 为准进行分析去重
    analyzed_tracker = get_analyzed_tracker(DATA_DIR / "analyzed_ids.json")
    cleaned = analyzed_tracker.cleanup()
    if cleaned > 0:
        logger.info(f"清理 analyzed_ids 过期记录: {cleaned} 条")

    analyzed_paper_ids = analyzed_tracker.get_paper_ids()
    analyzed_news_ids = analyzed_tracker.get_news_ids()

    papers_to_analyze = [p for p in existing_papers if p.id not in analyzed_paper_ids]
    news_to_analyze = [n for n in existing_news if n.id not in analyzed_news_ids]

    papers_skipped = len(existing_papers) - len(papers_to_analyze)
    news_skipped = len(existing_news) - len(news_to_analyze)

    logger.info(
        f"加载数据: {len(existing_papers)} 篇论文 "
        f"(analyzed_ids 已去重 {papers_skipped}, 待分析 {len(papers_to_analyze)}), "
        f"{len(existing_news)} 条热点 "
        f"(analyzed_ids 已去重 {news_skipped}, 待分析 {len(news_to_analyze)})"
    )

    if not existing_papers and not existing_news:
        logger.warning("无数据需要分析")
        return [], []

    # 如果全部已被 analyzed_ids 去重，直接返回
    if not papers_to_analyze and not news_to_analyze:
        logger.info("所有数据均已在 analyzed_ids 中，无需重复分析")
        return existing_papers, existing_news

    # 使用 LLM 客户端进行分析（仅分析未成功的数据）
    async with LLMClient() as llm_client:
        newly_analyzed_papers: list[AnalyzedPaper] = []
        newly_analyzed_news: list[AnalyzedNews] = []

        # 论文分析（仅分析未成功的）
        if papers_to_analyze:
            paper_analyzer = PaperLightAnalyzer(llm_client)
            # 将 AnalyzedPaper 转换回 Paper 进行分析
            papers_input = [
                Paper(**{k: v for k, v in p.model_dump().items() if k in Paper.model_fields})
                for p in papers_to_analyze
            ]
            newly_analyzed_papers = await paper_analyzer.analyze_batch(papers_input)
            stats = PaperLightAnalyzer.get_analysis_stats(newly_analyzed_papers)
            logger.info(
                f"论文分析完成: 成功 {stats['success']}/{stats['total']}, "
                f"成功率 {stats['success_rate']:.1%}"
            )

        # 热点分析（仅分析未成功的）
        if news_to_analyze:
            news_analyzer = NewsLightAnalyzer(llm_client)
            # 将 AnalyzedNews 转换回 NewsItem 进行分析
            news_input = [
                NewsItem(**{k: v for k, v in n.model_dump().items() if k in NewsItem.model_fields})
                for n in news_to_analyze
            ]
            newly_analyzed_news = await news_analyzer.analyze_batch(news_input)
            stats = NewsLightAnalyzer.get_analysis_stats(newly_analyzed_news)
            logger.info(
                f"热点分析完成: 成功 {stats['success']}/{stats['total']}, "
                f"成功率 {stats['success_rate']:.1%}"
            )

    # 合并结果：保留原列表，并用新分析结果覆盖对应 ID
    paper_by_id: dict[str, AnalyzedPaper] = {p.id: p for p in existing_papers}
    for p in newly_analyzed_papers:
        paper_by_id[p.id] = p
    final_papers = list(paper_by_id.values())

    news_by_id: dict[str, AnalyzedNews] = {n.id: n for n in existing_news}
    for n in newly_analyzed_news:
        news_by_id[n.id] = n
    final_news = list(news_by_id.values())

    # 保存分析结果（覆盖原文件）
    if final_papers:
        save_models_json(final_papers, papers_file, log_label="已分析论文")
    if final_news:
        save_models_json(final_news, news_file, log_label="已分析热点")

    # 分析成功后写回 analyzed_ids（只记录 success）
    analyzed_success_paper_ids = [p.id for p in newly_analyzed_papers if p.analysis_status == "success"]
    analyzed_success_news_ids = [n.id for n in newly_analyzed_news if n.analysis_status == "success"]
    if analyzed_success_paper_ids:
        analyzed_tracker.mark_papers(analyzed_success_paper_ids)
    if analyzed_success_news_ids:
        analyzed_tracker.mark_news(analyzed_success_news_ids)

    # 输出最终统计
    total_papers_success = len([p for p in final_papers if p.analysis_status == "success"])
    total_news_success = len([n for n in final_news if n.analysis_status == "success"])
    logger.info(
        f"浅度分析任务完成: 论文 {total_papers_success}/{len(final_papers)} 成功, "
        f"热点 {total_news_success}/{len(final_news)} 成功"
    )
    return final_papers, final_news


async def task_summary() -> Optional[Path]:
    """
    任务：生成日报

    Returns:
        日报文件路径，失败返回 None
    """
    logger.info("=" * 50)
    logger.info("开始执行任务: 生成日报")
    logger.info("=" * 50)

    today = get_today_date()
    papers_file = PAPERS_DIR / f"{today}.json"
    news_file = NEWS_DIR / f"{today}.json"

    # 加载分析后的数据（统一按 Analyzed schema 读取）
    papers = load_models_json(papers_file, AnalyzedPaper)
    news = load_models_json(news_file, AnalyzedNews)

    logger.info(f"加载分析数据: {len(papers)} 篇论文, {len(news)} 条热点")

    if not papers and not news:
        logger.warning("无数据可生成日报")
        return None

    # 生成日报
    generator = DailyReportGenerator(data_dir=DATA_DIR)
    report = await generator.generate(papers, news, date=today)

    # 保存日报
    file_path = await generator.save(report)

    logger.info(f"日报生成完成: {file_path}")
    return file_path


async def task_update_file_list() -> None:
    """
    任务：更新 file-list.json 索引

    扫描数据目录，更新前端需要的文件索引。
    """
    logger.info("=" * 50)
    logger.info("开始执行任务: 更新文件索引")
    logger.info("=" * 50)

    out_path = write_file_list(DATA_DIR)
    logger.info(f"文件索引更新完成: {out_path}")


async def task_notify() -> bool:
    """
    任务：发送飞书日报通知

    Returns:
        发送是否成功
    """
    logger.info("=" * 50)
    logger.info("开始执行任务: 发送通知")
    logger.info("=" * 50)

    today = get_today_date()
    report_file = REPORTS_DIR / f"{today}.json"

    if not report_file.exists():
        logger.warning(f"日报文件不存在: {report_file}")
        return False

    # 加载日报
    from src.models import DailyReport
    report_data = json.loads(report_file.read_text(encoding="utf-8"))
    report = DailyReport.model_validate(report_data)

    # 发送通知
    notifier = get_notifier()
    try:
        success = await notifier.send_daily_report(report)
        if success:
            logger.info("飞书通知发送成功")
        else:
            logger.warning("飞书通知发送失败或未配置")
        return success
    finally:
        await notifier.close()


async def run_all() -> int:
    """
    执行全部任务

    按顺序执行：arxiv → rss → analyze → summary → update_file_list → notify
    即使无新论文，也会继续执行后续任务（新闻获取、分析、日报等）。

    Returns:
        退出码
    """
    logger.info("=" * 60)
    logger.info("开始执行全部任务")
    logger.info("=" * 60)

    # 1. arXiv 获取（即使无新论文也继续后续任务）
    status = await task_arxiv()
    if status == DedupStatus.PROCESS_ERROR:
        logger.error("arXiv 获取出错")
        return 3

    # 2. RSS 获取
    await task_rss()

    # 3. 浅度分析
    await task_analyze()

    # 4. 生成日报
    await task_summary()

    # 5. 更新文件索引
    await task_update_file_list()

    # 6. 发送通知
    await task_notify()

    logger.info("=" * 60)
    logger.info("全部任务执行完成")
    logger.info("=" * 60)

    return 0


async def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="AI Insight Tracker 每日任务脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--task",
        choices=["arxiv", "rss", "analyze", "summary", "notify", "update-file-list", "all"],
        default="all",
        help="要执行的任务 (默认: all)",
    )
    parser.add_argument(
        "--skip-config-check",
        action="store_true",
        help="跳过配置检查（CI 环境使用）",
    )

    args = parser.parse_args()

    # 配置检查
    if not args.skip_config_check:
        if check_first_run():
            logger.error("首次运行，请先执行 ./setup.sh 初始化配置")
            return 1

        is_valid, errors = check_required_config()
        if not is_valid:
            logger.error("配置验证失败:")
            for error in errors:
                logger.error(f"  - {error}")
            return 1

    # 执行任务
    try:
        if args.task == "arxiv":
            status = await task_arxiv()
            # 单任务模式下，无新论文/无论文也视为成功（不应被 CI 判定为失败）
            return 3 if status == DedupStatus.PROCESS_ERROR else 0

        elif args.task == "rss":
            await task_rss()
            return 0

        elif args.task == "analyze":
            await task_analyze()
            return 0

        elif args.task == "summary":
            result = await task_summary()
            return 0 if result else 3

        elif args.task == "notify":
            success = await task_notify()
            return 0 if success else 3

        elif args.task == "update-file-list":
            await task_update_file_list()
            return 0

        elif args.task == "all":
            return await run_all()

    except Exception as e:
        logger.exception(f"任务执行出错: {e}")
        return 3


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

