"""
新闻获取器

统一 RSS 和 Crawler 两种获取方式，提供统一的接口。
支持历史去重，避免重复处理同一条新闻。
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from src.models import NewsItem, NewsSource, FetchType, RSSSource
from .rss_fetcher import AsyncRSSFetcher
from src.data_fetchers.crawler import AsyncNewsCrawler
from src.data_fetchers.ids_tracker import get_fetched_tracker
from .sources import load_news_sources

logger = logging.getLogger(__name__)


class NewsFetcher:
    """
    新闻获取器

    Features:
        - RSS 源使用内部的 AsyncRSSFetcher
        - Crawler 源使用 AsyncNewsCrawler
        - 统一输出为 NewsItem
    """

    def __init__(
        self,
        rss_timeout: float = 30.0,
        rss_max_concurrent: int = 10,
        crawler_max_concurrent: int = 3,
        crawler_timeout: float = 60.0,
    ):
        """
        初始化获取器

        Args:
            rss_timeout: RSS 请求超时
            rss_max_concurrent: RSS 最大并发数
            crawler_max_concurrent: Crawler 最大并发数（浏览器实例数）
            crawler_timeout: 页面加载超时
        """
        self._rss_fetcher = AsyncRSSFetcher(
            timeout=rss_timeout,
            max_concurrent=rss_max_concurrent,
        )
        self._crawler = AsyncNewsCrawler(
            max_concurrent=crawler_max_concurrent,
            timeout=crawler_timeout,
        )

    async def fetch_all(
        self,
        config_path: Optional[str] = None,
        hours: int = 168,  # 7 天，博客更新频率低
    ) -> list[NewsItem]:
        """
        获取所有新闻源

        Args:
            config_path: 配置文件路径
            hours: 时间窗口（小时）

        Returns:
            去重后的 NewsItem 列表
        """
        # 加载源配置
        try:
            sources = load_news_sources(config_path)
        except FileNotFoundError as e:
            logger.error(f"加载新闻源配置失败: {e}")
            return []

        enabled_sources = [s for s in sources if s.enabled]

        if not enabled_sources:
            logger.warning("没有启用的新闻源")
            return []

        logger.info(f"开始获取 {len(enabled_sources)} 个新闻源")

        # 分离 RSS 源和 Crawler 源
        rss_sources = [s for s in enabled_sources if s.fetch_type == FetchType.RSS]
        crawler_sources = [s for s in enabled_sources if s.fetch_type == FetchType.CRAWLER]

        # 并发获取 RSS 和 Crawler
        rss_task = self._fetch_rss_sources(rss_sources)
        crawler_task = self._crawler.fetch_all(crawler_sources)

        results = await asyncio.gather(
            rss_task,
            crawler_task,
            return_exceptions=True,
        )

        rss_items = results[0]
        crawler_items = results[1]

        # 处理结果
        all_items: list[NewsItem] = []

        if isinstance(rss_items, Exception):
            logger.error(f"RSS 获取失败: {rss_items}")
            rss_count = 0
        else:
            all_items.extend(rss_items)
            rss_count = len(rss_items)

        if isinstance(crawler_items, Exception):
            logger.error(f"Crawler 获取失败: {crawler_items}")
            crawler_count = 0
        else:
            all_items.extend(crawler_items)
            crawler_count = len(crawler_items)

        # 时间过滤
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        filtered_items = []
        for item in all_items:
            try:
                item_time = item.published
                if item_time.tzinfo is None:
                    item_time = item_time.replace(tzinfo=timezone.utc)
                if item_time >= cutoff:
                    filtered_items.append(item)
            except Exception:
                # 如果日期解析失败，保留该条目
                filtered_items.append(item)

        # URL 去重（同批次内）
        unique_items = self._dedup_by_url(filtered_items)

        # 历史去重（抓取去重：排除已抓取的新闻）
        tracker = get_fetched_tracker()
        processed_ids = tracker.get_news_ids()
        new_items = [
            item for item in unique_items
            if item.id not in processed_ids
        ]
        history_dedup_count = len(unique_items) - len(new_items)

        # 按权重和时间排序
        sorted_items = sorted(
            new_items,
            key=lambda x: (x.weight, x.published),
            reverse=True,
        )

        logger.info(
            f"获取完成: RSS {rss_count} 条, "
            f"Crawler {crawler_count} 条, "
            f"同批次去重后 {len(unique_items)} 条, "
            f"历史去重 {history_dedup_count} 条, "
            f"新内容 {len(sorted_items)} 条"
        )

        return sorted_items

    async def _fetch_rss_sources(
        self,
        sources: list[NewsSource],
    ) -> list[NewsItem]:
        """
        获取 RSS 源
        """
        if not sources:
            return []

        # 转换为 RSSSource 格式
        rss_sources = []
        source_map: dict[str, NewsSource] = {}

        for s in sources:
            if s.rss_url:
                rss_source = RSSSource(
                    name=s.name,
                    url=s.rss_url,
                    category="ai",
                    language=s.language,
                    weight=s.weight,
                    enabled=True,
                )
                rss_sources.append(rss_source)
                source_map[s.name] = s

        if not rss_sources:
            return []

        items = await self._rss_fetcher.fetch_all(rss_sources)

        # 为 RSS 获取的项目添加扩展字段
        for item in items:
            source = source_map.get(item.source_name)
            if source:
                item.company = source.company
                item.fetch_type = FetchType.RSS

        return items

    def _dedup_by_url(self, items: list[NewsItem]) -> list[NewsItem]:
        """基于 URL ID 去重"""
        seen_ids: set[str] = set()
        unique_items: list[NewsItem] = []

        for item in items:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                unique_items.append(item)

        return unique_items

