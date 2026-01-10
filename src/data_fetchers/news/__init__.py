"""
新闻源获取模块

统一 RSS 和 Crawler 两种获取方式。
"""

"""
注意：这里采用 lazy import，避免仅加载配置（sources.py）时就触发 RSS 解析依赖
（例如 feedparser）。
"""

from importlib import import_module
from typing import Optional, Any

__all__ = [
    "NewsFetcher",
    "load_news_sources",
    "fetch_news",
]


async def fetch_news(
    config_path: Optional[str] = None,
    hours: int = 168,
) -> list["NewsItem"]:
    """
    获取新闻源

    Args:
        config_path: 配置文件路径
        hours: 时间窗口（小时）

    Returns:
        NewsItem 列表
    """
    from src.models import NewsItem  # noqa: F401
    from .fetcher import NewsFetcher
    fetcher = NewsFetcher()
    return await fetcher.fetch_all(config_path, hours)


# 允许 `from src.data_fetchers.news import NewsFetcher` 等写法，同时保持 lazy。
_EXPORTS: dict[str, str] = {
    "NewsFetcher": "src.data_fetchers.news.fetcher",
    "load_news_sources": "src.data_fetchers.news.sources",
}


def __getattr__(name: str) -> Any:  # pragma: no cover
    mod = _EXPORTS.get(name)
    if not mod:
        raise AttributeError(name)
    module = import_module(mod)
    return getattr(module, name)


def __dir__() -> list[str]:  # pragma: no cover
    return sorted(list(globals().keys()) + __all__)

