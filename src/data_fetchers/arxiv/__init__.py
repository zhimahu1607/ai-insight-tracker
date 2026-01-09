"""
arXiv API 客户端模块

提供异步的 arXiv 论文获取能力，包括：
- 按分类查询最新论文
- 按论文 ID 批量获取
- 全量历史去重

Usage:
    from src.data_fetchers.arxiv import fetch_arxiv_papers

    papers = await fetch_arxiv_papers(
        categories=["cs.AI", "cs.CL"],
        days=1,
        dedup=True,
    )
"""

from .client import AsyncArxivClient
from .query import build_category_query, build_id_query
from .dedup import load_all_historical_ids, dedup_papers
from typing import Optional
from pathlib import Path

__all__ = [
    "AsyncArxivClient",
    "build_category_query",
    "build_id_query",
    "load_all_historical_ids",
    "dedup_papers",
    "fetch_arxiv_papers",
]


async def fetch_arxiv_papers(
    categories: Optional[list[str]] = None,
    days: int = 1,
    dedup: bool = True,
) -> list:
    """
    获取 arXiv 论文

    Args:
        categories: 分类列表，None 时从配置读取
        days: 获取最近几天的论文
        dedup: 是否使用 ProcessedTracker 进行历史去重

    Returns:
        去重后的论文列表
    """
    from src.config import get_settings
    from src.models import Paper
    from src.data_fetchers.processed_tracker import get_processed_tracker

    settings = get_settings()

    # 使用配置中的分类（如未指定）
    if categories is None:
        categories = settings.arxiv.categories

    # 创建客户端
    client = AsyncArxivClient(
        timeout=settings.arxiv.timeout,
        max_results_per_category=settings.arxiv.max_results,
        delay_between_requests=settings.arxiv.request_delay,
    )

    # 获取论文
    papers = await client.fetch_recent_papers(categories=categories, days=days)

    # 使用 ProcessedTracker 进行历史去重（保留30天记录）
    if dedup:
        tracker = get_processed_tracker(Path("data/processed_ids.json"))
        processed_ids = tracker.get_processed_paper_ids()
        papers = [p for p in papers if p.id not in processed_ids]

    return papers

