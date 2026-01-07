"""
数据采集模块

提供 arXiv API 和新闻源数据获取能力，是整个系统的数据入口。

设计原则:
    - 全异步设计，统一使用 aiohttp + asyncio
    - arXiv 数据通过 arXiv API 获取
    - 新闻源通过 NewsFetcher 统一 RSS 和 Crawler
    - ProcessedTracker 管理已处理 ID，支持7天自动清理

Usage:
    from src.data_fetchers import fetch_arxiv_papers, fetch_news

    # 获取 arXiv 论文
    papers = await fetch_arxiv_papers(
        categories=["cs.AI", "cs.CL"],
        hours=25,
        dedup=True,
    )

    # 获取新闻
    news = await fetch_news(
        config_path="config/news_sources.yaml",
        hours=168,
    )
"""

from .arxiv import (
    AsyncArxivClient,
    build_category_query,
    build_id_query,
    load_all_historical_ids,
    dedup_papers,
    fetch_arxiv_papers,
)
from .news import (
    NewsFetcher,
    load_news_sources,
    fetch_news,
)
from .processed_tracker import (
    ProcessedTracker,
    get_processed_tracker,
    reset_processed_tracker,
)

__all__ = [
    # arXiv
    "AsyncArxivClient",
    "build_category_query",
    "build_id_query",
    "load_all_historical_ids",
    "dedup_papers",
    "fetch_arxiv_papers",
    # News
    "NewsFetcher",
    "load_news_sources",
    "fetch_news",
    # ProcessedTracker
    "ProcessedTracker",
    "get_processed_tracker",
    "reset_processed_tracker",
]
