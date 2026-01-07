"""
新闻源获取模块

统一 RSS 和 Crawler 两种获取方式。
"""

from typing import Optional

from src.models import NewsItem
from .fetcher import NewsFetcher
from .sources import load_news_sources

__all__ = [
    "NewsFetcher",
    "load_news_sources",
    "fetch_news",
]


async def fetch_news(
    config_path: Optional[str] = None,
    hours: int = 168,
) -> list[NewsItem]:
    """
    获取新闻源

    Args:
        config_path: 配置文件路径
        hours: 时间窗口（小时）

    Returns:
        NewsItem 列表
    """
    fetcher = NewsFetcher()
    return await fetcher.fetch_all(config_path, hours)

