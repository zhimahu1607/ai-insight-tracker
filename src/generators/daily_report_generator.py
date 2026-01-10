"""
日报生成器

负责聚合论文和热点数据，生成每日报告。
支持 LLM 生成智能总结和模板化总结两种方式。
"""

import asyncio
import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage

from src.config import get_settings
from src.llm import LLMClient
from src.models import (
    AnalyzedNews,
    AnalyzedPaper,
    DailyReport,
    DailyStats,
)
from src.prompts import (
    REPORT_SYSTEM_PROMPT,
    CATEGORY_SUMMARY_USER_PROMPT,
    NEWS_SUMMARY_USER_PROMPT,
    DAILY_SUMMARY_USER_PROMPT,
)
from src.file_index import write_file_list


logger = logging.getLogger(__name__)


class DailyReportGenerator:
    """
    日报生成器

    负责聚合分析后的论文和热点数据，生成结构化的每日报告。

    Usage:
        generator = DailyReportGenerator()
        report = await generator.generate(papers, news)
        await generator.save(report)
    """

    # 数据存储路径
    DATA_DIR = Path("data")
    REPORTS_DIR = DATA_DIR / "reports"
    FILE_LIST_PATH = DATA_DIR / "file-list.json"

    def __init__(
        self,
        use_llm_summary: bool = True,
        data_dir: Optional[Path] = None,
    ):
        """
        初始化日报生成器

        Args:
            use_llm_summary: 是否使用 LLM 生成总结，默认 True
            data_dir: 自定义数据目录，默认为项目根目录下的 data/
        """
        self._use_llm_summary = use_llm_summary
        
        # 获取配置中的分类列表
        self.settings = get_settings()
        self.categories = self.settings.arxiv.categories

        # 设置数据目录
        if data_dir:
            self.DATA_DIR = data_dir
            self.REPORTS_DIR = data_dir / "reports"
            self.FILE_LIST_PATH = data_dir / "file-list.json"

    async def generate(
        self,
        papers: list[AnalyzedPaper],
        news: list[AnalyzedNews],
        date: Optional[str] = None,
    ) -> DailyReport:
        """
        生成每日报告

        Args:
            papers: 已分析的论文列表
            news: 已分析的热点列表
            date: 报告日期，格式 YYYY-MM-DD，默认为今日

        Returns:
            DailyReport 实例
        """
        report_date = date or datetime.now().strftime("%Y-%m-%d")

        # 按发布时间排序论文（成功分析的优先，然后按发布时间降序）
        sorted_papers = self._sort_papers(papers)

        # 按权重和发布时间排序热点
        sorted_news = self._sort_news(news)

        # 生成统计信息
        stats = self._compute_stats(sorted_papers, sorted_news)

        # 生成总结 (Daily Summary + Category Summaries + News Summary)
        daily_summary, category_summaries, news_summary = await self._generate_full_report(
            sorted_papers, sorted_news, stats
        )

        report = DailyReport(
            date=report_date,
            summary=daily_summary,
            category_summaries=category_summaries,
            news_summary=news_summary,
            stats=stats,
            generated_at=datetime.now(),
        )

        logger.info(
            f"日报生成完成: {report_date}, "
            f"论文 {len(sorted_papers)} 篇, 热点 {len(sorted_news)} 条"
        )

        return report

    def _sort_papers(self, papers: list[AnalyzedPaper]) -> list[AnalyzedPaper]:
        """
        排序论文列表

        排序规则:
        1. 分析成功的在前
        2. 按发布时间降序
        """

        def sort_key(paper: AnalyzedPaper) -> tuple:
            # 成功的排前面 (0 < 1，所以成功给 0)
            status_order = 0 if paper.analysis_status == "success" else 1

            # 发布时间降序
            pub_time = -paper.published.timestamp() if paper.published else 0

            return (status_order, pub_time)

        return sorted(papers, key=sort_key)

    def _sort_news(self, news: list[AnalyzedNews]) -> list[AnalyzedNews]:
        """
        排序热点列表

        排序规则:
        1. 分析成功的在前
        2. 按权重降序
        3. 按发布时间降序
        """

        def sort_key(item: AnalyzedNews) -> tuple:
            status_order = 0 if item.analysis_status == "success" else 1

            # 权重降序（取负数）
            weight = -item.weight

            pub_time = -item.published.timestamp() if item.published else 0

            return (status_order, weight, pub_time)

        return sorted(news, key=sort_key)

    def _compute_stats(
        self,
        papers: list[AnalyzedPaper],
        news: list[AnalyzedNews],
    ) -> DailyStats:
        """计算统计信息"""
        # 论文按主分类统计
        papers_by_category: Counter[str] = Counter()
        for paper in papers:
            papers_by_category[paper.primary_category] += 1

        # 热点按分类统计
        news_by_category: Counter[str] = Counter()
        for item in news:
            if item.light_analysis:
                news_by_category[item.light_analysis.category] += 1
            else:
                news_by_category[item.source_category] += 1

        # 提取热门关键词（从论文标签和热点关键词）
        keyword_counter: Counter[str] = Counter()

        for paper in papers:
            if paper.light_analysis:
                for tag in paper.light_analysis.tags:
                    keyword_counter[tag] += 1

        for item in news:
            if item.light_analysis:
                for kw in item.light_analysis.keywords:
                    keyword_counter[kw] += 1

        # 取前 10 个热门关键词
        top_keywords = [kw for kw, _ in keyword_counter.most_common(10)]

        return DailyStats(
            total_papers=len(papers),
            papers_by_category=dict(papers_by_category),
            total_news=len(news),
            news_by_category=dict(news_by_category),
            top_keywords=top_keywords,
        )

    async def _generate_full_report(
        self,
        papers: list[AnalyzedPaper],
        news: list[AnalyzedNews],
        stats: DailyStats,
    ) -> tuple[str, dict[str, str], str]:
        """
        生成完整日报内容 (Daily Summary, Category Summaries, News Summary)
        """
        if not self._use_llm_summary:
            template_summary = self._generate_template_summary(stats)
            return template_summary, {}, ""

        try:
            # 1. 异步生成各领域的总结
            category_summaries_task = self._generate_category_summaries(papers)
            
            # 2. 异步生成新闻总结
            news_summary_task = self._generate_news_summary(news)

            # 并发执行
            category_summaries, news_summary = await asyncio.gather(
                category_summaries_task, news_summary_task
            )

            # 3. 基于上述总结生成 Daily Summary
            daily_summary = await self._generate_daily_summary(
                category_summaries, news_summary
            )

            return daily_summary, category_summaries, news_summary

        except Exception as e:
            logger.error(f"LLM 生成报告失败: {e}", exc_info=True)
            return self._generate_template_summary(stats), {}, ""

    async def _generate_category_summaries(
        self, papers: list[AnalyzedPaper]
    ) -> dict[str, str]:
        """按领域生成论文总结"""
        tasks = []
        categories = []

        # 按领域分组论文
        papers_map = {cat: [] for cat in self.categories}
        for paper in papers:
            # 优先匹配 primary_category，如果不在配置列表中，暂不处理或归入 'Other' (此处仅处理配置列表中的)
            if paper.primary_category in papers_map:
                papers_map[paper.primary_category].append(paper)
        
        # 为每个有论文的领域创建任务
        for cat, cat_papers in papers_map.items():
            if not cat_papers:
                continue
            
            categories.append(cat)
            tasks.append(self._summarize_single_category(cat, cat_papers))

        if not tasks:
            return {}

        results = await asyncio.gather(*tasks)
        return dict(zip(categories, results))

    async def _summarize_single_category(
        self, category: str, papers: list[AnalyzedPaper]
    ) -> str:
        """总结单个领域的论文"""
        # 构建论文内容字符串
        # 限制每篇论文的长度以避免 token溢出，只取 overview 和 tags
        papers_content = []
        for p in papers:
            if p.light_analysis:
                info = (
                    f"Title: {p.title}\n"
                    f"ID: {p.id}\n"
                    f"Overview: {p.light_analysis.overview}\n"
                    f"Tags: {', '.join(p.light_analysis.tags)}\n"
                )
                papers_content.append(info)
        
        content_str = "\n---\n".join(papers_content)
        
        prompt = CATEGORY_SUMMARY_USER_PROMPT.format(
            category=category,
            papers_content=content_str
        )

        async with LLMClient(temperature=0.5) as client:
            response = await client.chat([
                SystemMessage(content=REPORT_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
        
        return response.strip()

    async def _generate_news_summary(self, news: list[AnalyzedNews]) -> str:
        """生成新闻总结"""
        if not news:
            return "今日暂无重大热点新闻。"

        news_content = []
        for n in news:
            if n.light_analysis:
                info = (
                    f"Title: {n.title}\n"
                    f"Source: {n.source_name}\n"
                    f"Summary: {n.light_analysis.summary}\n"
                    f"Category: {n.light_analysis.category}\n"
                )
                news_content.append(info)
        
        content_str = "\n---\n".join(news_content)

        prompt = NEWS_SUMMARY_USER_PROMPT.format(news_content=content_str)

        async with LLMClient(temperature=0.5) as client:
            response = await client.chat([
                SystemMessage(content=REPORT_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
        
        return response.strip()

    async def _generate_daily_summary(
        self, category_summaries: dict[str, str], news_summary: str
    ) -> str:
        """基于各部分总结生成 Daily Summary"""
        
        # 格式化领域总结
        cat_summaries_str = ""
        for cat, summary in category_summaries.items():
            cat_summaries_str += f"### {cat}\n{summary}\n\n"
        
        if not cat_summaries_str:
            cat_summaries_str = "今日无论文收录。"

        prompt = DAILY_SUMMARY_USER_PROMPT.format(
            category_summaries_content=cat_summaries_str,
            news_summary_content=news_summary
        )

        async with LLMClient(temperature=0.7) as client:
            response = await client.chat([
                SystemMessage(content=REPORT_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
        
        return response.strip()

    def _generate_template_summary(self, stats: DailyStats) -> str:
        """使用模板生成总结"""
        # 获取前 5 个论文分类
        top_categories = sorted(
            stats.papers_by_category.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]
        category_str = "、".join([cat for cat, _ in top_categories]) if top_categories else "无"

        # 获取前 5 个热门关键词
        keywords_str = "、".join(stats.top_keywords[:5]) if stats.top_keywords else "无"

        return (
            f"今日共收录 {stats.total_papers} 篇论文，{stats.total_news} 条热点资讯。"
            f"热门领域：{category_str}。"
            f"热门关键词：{keywords_str}。"
        )

    async def save(self, report: DailyReport) -> Path:
        """
        保存日报到文件

        Args:
            report: 日报实例

        Returns:
            保存的文件路径
        """
        # 确保目录存在
        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # 保存日报
        file_path = self.REPORTS_DIR / f"{report.date}.json"
        file_path.write_text(
            report.model_dump_json(indent=2, by_alias=True),
            encoding="utf-8",
        )

        logger.info(f"日报已保存: {file_path}")

        # 更新文件索引（统一由 file_index 生成，避免索引漂移）
        write_file_list(self.DATA_DIR)

        return file_path

    # NOTE: 原先的 _update_file_list(date) 已移除，统一使用 src.file_index.write_file_list()
