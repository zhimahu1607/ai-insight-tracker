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

from __future__ import annotations

from .client import AsyncArxivClient
from .query import build_category_query, build_id_query
from .dedup import load_all_historical_ids, dedup_papers
from typing import Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from src.models import Paper

__all__ = [
    "AsyncArxivClient",
    "build_category_query",
    "build_id_query",
    "load_all_historical_ids",
    "dedup_papers",
    "fetch_arxiv_papers",
    "fetch_arxiv_papers_by_ids",
    "fetch_arxiv_paper_by_id",
]


def _create_client_from_settings(settings=None) -> AsyncArxivClient:
    """
    从 settings.arxiv 创建 AsyncArxivClient，确保所有入口使用一致的配置映射。
    """
    from src.config import get_settings

    if settings is None:
        settings = get_settings()

    return AsyncArxivClient(
        timeout=settings.arxiv.timeout,
        max_results_per_category=settings.arxiv.max_results,
        max_pages_per_category=getattr(settings.arxiv, "max_pages", 20),
        delay_between_requests=settings.arxiv.request_delay,
    )


async def fetch_arxiv_papers(
    categories: Optional[list[str]] = None,
    hours: int = 25,
    dedup: bool = True,
    ) -> list[Paper]:
    """
    获取 arXiv 论文

    Args:
        categories: 分类列表，None 时从配置读取
        hours: 获取最近多少小时的论文
        dedup: 是否使用 ProcessedTracker 进行历史去重

    Returns:
        去重后的论文列表
    """
    from src.config import get_settings
    from src.data_fetchers.ids_tracker import get_fetched_tracker

    settings = get_settings()

    # 使用配置中的分类（如未指定）
    if categories is None:
        categories = settings.arxiv.categories

    # 创建客户端
    client = _create_client_from_settings(settings)

    # 获取论文
    papers = await client.fetch_recent_papers(categories=categories, hours=hours)

    # 抓取去重：使用 fetched_ids.json 进行历史去重（保留30天记录）
    if dedup:
        tracker = get_fetched_tracker(Path("data/fetched_ids.json"))
        processed_ids = tracker.get_paper_ids()
        papers = [p for p in papers if p.id not in processed_ids]

    return papers


async def fetch_arxiv_papers_by_ids(paper_ids: list[str]) -> list[Paper]:
    """
    按论文 ID 批量获取论文详情（统一入口，使用 settings.arxiv 初始化 client）。
    """
    from src.models import Paper

    if not paper_ids:
        return []

    client = _create_client_from_settings()
    return await client.fetch_by_ids(paper_ids)


async def fetch_arxiv_paper_by_id(paper_id: str) -> Optional[Paper]:
    """
    按论文 ID 获取单篇论文详情（统一入口，使用 settings.arxiv 初始化 client）。
    """
    papers = await fetch_arxiv_papers_by_ids([paper_id])
    return papers[0] if papers else None

