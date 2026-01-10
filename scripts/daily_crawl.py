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
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings, check_first_run, check_required_config
from src.data_fetchers.arxiv import AsyncArxivClient
from src.data_fetchers.status import DedupStatus
from src.data_fetchers.processed_tracker import get_processed_tracker
from src.data_fetchers.news import NewsFetcher
from src.agents.paper import PaperLightAnalyzer
from src.agents.news import NewsLightAnalyzer
from src.generators import DailyReportGenerator
from src.llm import LLMClient
from src.models import Paper, NewsItem, AnalyzedPaper, AnalyzedNews
from src.notifiers.feishu import get_notifier


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


def save_papers_json(papers: list[Paper], file_path: Path) -> None:
    """保存论文列表到 JSON 文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    # 确保后缀为 .json
    if file_path.suffix == '.jsonl':
        file_path = file_path.with_suffix('.json')
    
    with open(file_path, "w", encoding="utf-8") as f:
        # 转换为字典列表
        data = [json.loads(p.model_dump_json()) for p in papers]
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"保存 {len(papers)} 篇论文到 {file_path}")


def save_analyzed_papers_json(papers: list[AnalyzedPaper], file_path: Path) -> None:
    """保存分析后的论文到 JSON 文件（覆盖原文件）"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    # 确保后缀为 .json
    if file_path.suffix == '.jsonl':
        file_path = file_path.with_suffix('.json')

    with open(file_path, "w", encoding="utf-8") as f:
        # 转换为字典列表
        data = [json.loads(p.model_dump_json()) for p in papers]
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"保存 {len(papers)} 篇已分析论文到 {file_path}")


def load_papers_json(file_path: Path) -> list[Paper]:
    """从 JSON 文件加载论文列表"""
    # 兼容 .jsonl 和 .json
    if not file_path.exists():
        # 尝试查找另一种后缀
        alt_path = file_path.with_suffix('.jsonl') if file_path.suffix == '.json' else file_path.with_suffix('.json')
        if alt_path.exists():
            file_path = alt_path
        else:
            return []

    papers = []
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.suffix == '.jsonl':
            for line in f:
                line = line.strip()
                if line:
                    papers.append(Paper.model_validate_json(line))
        else:
            try:
                data = json.load(f)
                for item in data:
                    papers.append(Paper.model_validate(item))
            except json.JSONDecodeError:
                logger.warning(f"JSON 解析失败: {file_path}")
                return []
    return papers


def load_analyzed_papers_json(file_path: Path) -> list[AnalyzedPaper]:
    """从 JSON 文件加载已分析的论文列表"""
    # 兼容 .jsonl 和 .json
    if not file_path.exists():
        # 尝试查找另一种后缀
        alt_path = file_path.with_suffix('.jsonl') if file_path.suffix == '.json' else file_path.with_suffix('.json')
        if alt_path.exists():
            file_path = alt_path
        else:
            return []

    papers = []
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.suffix == '.jsonl':
            for line in f:
                line = line.strip()
                if line:
                    papers.append(AnalyzedPaper.model_validate_json(line))
        else:
            try:
                data = json.load(f)
                for item in data:
                    papers.append(AnalyzedPaper.model_validate(item))
            except json.JSONDecodeError:
                logger.warning(f"JSON 解析失败: {file_path}")
                return []
    return papers


def save_news_json(news: list[NewsItem], file_path: Path) -> None:
    """保存热点列表到 JSON 文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    # 确保后缀为 .json
    if file_path.suffix == '.jsonl':
        file_path = file_path.with_suffix('.json')

    with open(file_path, "w", encoding="utf-8") as f:
        # 转换为字典列表
        data = [json.loads(item.model_dump_json()) for item in news]
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"保存 {len(news)} 条热点到 {file_path}")


def save_analyzed_news_json(news: list[AnalyzedNews], file_path: Path) -> None:
    """保存分析后的热点到 JSON 文件（覆盖原文件）"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    # 确保后缀为 .json
    if file_path.suffix == '.jsonl':
        file_path = file_path.with_suffix('.json')

    with open(file_path, "w", encoding="utf-8") as f:
        # 转换为字典列表
        data = [json.loads(item.model_dump_json()) for item in news]
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"保存 {len(news)} 条已分析热点到 {file_path}")


def load_news_json(file_path: Path) -> list[NewsItem]:
    """从 JSON 文件加载热点列表"""
    # 兼容 .jsonl 和 .json
    if not file_path.exists():
        # 尝试查找另一种后缀
        alt_path = file_path.with_suffix('.jsonl') if file_path.suffix == '.json' else file_path.with_suffix('.json')
        if alt_path.exists():
            file_path = alt_path
        else:
            return []

    news = []
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.suffix == '.jsonl':
            for line in f:
                line = line.strip()
                if line:
                    news.append(NewsItem.model_validate_json(line))
        else:
            try:
                data = json.load(f)
                for item in data:
                    news.append(NewsItem.model_validate(item))
            except json.JSONDecodeError:
                logger.warning(f"JSON 解析失败: {file_path}")
                return []
    return news


def load_analyzed_news_json(file_path: Path) -> list[AnalyzedNews]:
    """从 JSON 文件加载已分析的热点列表"""
    # 兼容 .jsonl 和 .json
    if not file_path.exists():
        # 尝试查找另一种后缀
        alt_path = file_path.with_suffix('.jsonl') if file_path.suffix == '.json' else file_path.with_suffix('.json')
        if alt_path.exists():
            file_path = alt_path
        else:
            return []

    news = []
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.suffix == '.jsonl':
            for line in f:
                line = line.strip()
                if line:
                    news.append(AnalyzedNews.model_validate_json(line))
        else:
            try:
                data = json.load(f)
                for item in data:
                    news.append(AnalyzedNews.model_validate(item))
            except json.JSONDecodeError:
                logger.warning(f"JSON 解析失败: {file_path}")
                return []
    return news


async def task_arxiv() -> tuple[list[Paper], int]:
    """
    任务：获取 arXiv 论文并去重

    使用 ProcessedTracker 进行历史去重，支持30天自动清理。
    默认获取过去25小时内发布的论文。

    Returns:
        (新论文列表, 状态码)
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
    tracker = get_processed_tracker(DATA_DIR / "processed_ids.json")
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
    import os
    hours = int(os.environ.get("ARXIV_HOURS", "25"))
    papers = await client.fetch_recent_papers(categories, hours=hours)
    logger.info(f"获取到 {len(papers)} 篇论文（过去 {hours} 小时）")

    if not papers:
        logger.warning("未获取到任何论文")
        return DedupStatus.NO_NEW_CONTENT

    # 使用 ProcessedTracker 去重
    processed_ids = tracker.get_processed_paper_ids()
    new_papers = [p for p in papers if p.id not in processed_ids]
    duplicates_count = len(papers) - len(new_papers)

    logger.info(
        f"去重完成: 获取 {len(papers)} 篇, "
        f"历史重复 {duplicates_count} 篇, "
        f"新论文 {len(new_papers)} 篇"
    )

    if not new_papers:
        logger.info("无新论文")
        # 仍然返回空列表和 HAS_NEW_CONTENT 状态，允许后续任务继续执行
        # （新闻获取、分析、日报生成等不应因无新论文而跳过）
        return DedupStatus.HAS_NEW_CONTENT

    # 保存新论文
    today = get_today_date()
    file_path = PAPERS_DIR / f"{today}.json"
    save_papers_json(new_papers, file_path)

    # 标记为已处理
    tracker.mark_papers_processed([p.id for p in new_papers])

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

    # 保存热点
    today = get_today_date()
    file_path = NEWS_DIR / f"{today}.json"
    save_news_json(news, file_path)

    # 标记为已处理
    tracker = get_processed_tracker(DATA_DIR / "processed_ids.json")
    tracker.mark_news_processed([item.id for item in news])

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

    # 加载今日数据（优先加载 AnalyzedPaper/AnalyzedNews 格式，保留分析状态）
    # 如果文件包含分析结果，使用 load_analyzed_xxx；否则回退到 load_xxx
    existing_papers = load_analyzed_papers_json(papers_file)
    existing_news = load_analyzed_news_json(news_file)

    # 如果加载失败或为空，尝试加载原始格式（兼容首次分析场景）
    if not existing_papers:
        raw_papers = load_papers_json(papers_file)
        # 将 Paper 转换为 AnalyzedPaper（analysis_status 默认为 pending）
        existing_papers = [
            AnalyzedPaper(**p.model_dump(), analysis_status="pending")
            for p in raw_papers
        ]
    if not existing_news:
        raw_news = load_news_json(news_file)
        # 将 NewsItem 转换为 AnalyzedNews（analysis_status 默认为 pending）
        existing_news = [
            AnalyzedNews(**n.model_dump(), analysis_status="pending")
            for n in raw_news
        ]

    # 分离已成功和待分析的数据
    papers_done = [p for p in existing_papers if p.analysis_status == "success"]
    papers_to_analyze = [p for p in existing_papers if p.analysis_status != "success"]
    news_done = [n for n in existing_news if n.analysis_status == "success"]
    news_to_analyze = [n for n in existing_news if n.analysis_status != "success"]

    logger.info(
        f"加载数据: {len(existing_papers)} 篇论文 "
        f"(已完成 {len(papers_done)}, 待分析 {len(papers_to_analyze)}), "
        f"{len(existing_news)} 条热点 "
        f"(已完成 {len(news_done)}, 待分析 {len(news_to_analyze)})"
    )

    if not existing_papers and not existing_news:
        logger.warning("无数据需要分析")
        return [], []

    # 如果全部已完成，直接返回
    if not papers_to_analyze and not news_to_analyze:
        logger.info("所有数据已分析完成，无需重复分析")
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

    # 合并结果：已完成 + 新分析
    final_papers = papers_done + newly_analyzed_papers
    final_news = news_done + newly_analyzed_news

    # 保存分析结果（覆盖原文件）
    if final_papers:
        save_analyzed_papers_json(final_papers, papers_file)
    if final_news:
        save_analyzed_news_json(final_news, news_file)

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

    # 加载分析后的数据
    papers = load_analyzed_papers_json(papers_file)
    news = load_analyzed_news_json(news_file)

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

    file_list_path = DATA_DIR / "file-list.json"

    # 扫描各目录
    papers_files = sorted(
        [f.name for f in PAPERS_DIR.glob("*.json")],
        reverse=True,
    ) if PAPERS_DIR.exists() else []

    news_files = sorted(
        [f.name for f in NEWS_DIR.glob("*.json")],
        reverse=True,
    ) if NEWS_DIR.exists() else []

    reports_files = sorted(
        [f.name for f in REPORTS_DIR.glob("*.json")],
        reverse=True,
    ) if REPORTS_DIR.exists() else []

    file_list = {
        "papers": papers_files,
        "news": news_files,
        "reports": reports_files,
    }

    # 保存索引
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(file_list_path, "w", encoding="utf-8") as f:
        json.dump(file_list, f, indent=2, ensure_ascii=False)

    logger.info(
        f"文件索引更新完成: "
        f"论文 {len(papers_files)} 个, "
        f"热点 {len(news_files)} 个, "
        f"日报 {len(reports_files)} 个"
    )


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

