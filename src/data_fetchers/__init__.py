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

"""
注意：这里采用 lazy import，避免仅为了使用某个子模块（例如 crawler/news）
就触发 arXiv/RSS 等可选依赖的导入（比如 feedparser）。

对外 API 保持不变：依旧支持
    from src.data_fetchers import fetch_news, NewsFetcher, fetch_arxiv_papers ...
"""

from importlib import import_module
from typing import Any

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


_EXPORTS: dict[str, str] = {
    # arXiv
    "AsyncArxivClient": "src.data_fetchers.arxiv",
    "build_category_query": "src.data_fetchers.arxiv",
    "build_id_query": "src.data_fetchers.arxiv",
    "load_all_historical_ids": "src.data_fetchers.arxiv",
    "dedup_papers": "src.data_fetchers.arxiv",
    "fetch_arxiv_papers": "src.data_fetchers.arxiv",
    # News
    "NewsFetcher": "src.data_fetchers.news",
    "load_news_sources": "src.data_fetchers.news",
    "fetch_news": "src.data_fetchers.news",
    # ProcessedTracker
    "ProcessedTracker": "src.data_fetchers.processed_tracker",
    "get_processed_tracker": "src.data_fetchers.processed_tracker",
    "reset_processed_tracker": "src.data_fetchers.processed_tracker",
}


def __getattr__(name: str) -> Any:  # pragma: no cover
    mod = _EXPORTS.get(name)
    if not mod:
        raise AttributeError(name)
    module = import_module(mod)
    return getattr(module, name)


def __dir__() -> list[str]:  # pragma: no cover
    return sorted(list(globals().keys()) + __all__)
