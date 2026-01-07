"""
RSS 异步获取器（内部模块）

用于获取有 RSS feed 的新闻源，作为 NewsFetcher 的内部组件。
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

import aiohttp

from src.models import RSSSource, NewsItem
from .rss_parser import parse_feed_sync

logger = logging.getLogger(__name__)


class AsyncRSSFetcher:
    """
    异步 RSS 获取器

    Features:
        - 使用 aiohttp 异步获取数据
        - Semaphore 控制最大并发数
        - 容错设计：单个源失败不影响其他源
        - Session 复用：在 fetch_all 中创建单个 ClientSession
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_concurrent: int = 20,
        max_retries: int = 3,
    ):
        """
        初始化获取器

        Args:
            timeout: HTTP 请求超时（秒）
            max_concurrent: 最大并发数
            max_retries: 最大重试次数
        """
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._max_concurrent = max_concurrent
        self._max_retries = max_retries
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_all(self, sources: list[RSSSource]) -> list[NewsItem]:
        """
        并发获取所有启用的 RSS 源

        Args:
            sources: RSS 源列表

        Returns:
            合并后的 NewsItem 列表
        """
        if not sources:
            logger.warning("没有 RSS 源需要获取")
            return []

        logger.info(f"开始获取 {len(sources)} 个 RSS 源")

        # 创建单个 Session 复用连接池
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            # 并发获取所有源
            tasks = [
                self._fetch_source(session, source)
                for source in sources
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_items: list[NewsItem] = []
        success_count = 0
        fail_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"获取 RSS 源失败 ({sources[i].name}): {result}")
                fail_count += 1
            else:
                all_items.extend(result)
                success_count += 1

        logger.info(
            f"RSS 获取完成: 成功 {success_count}/{len(sources)}, "
            f"失败 {fail_count}, 共 {len(all_items)} 条"
        )

        return all_items

    async def _fetch_source(
        self,
        session: aiohttp.ClientSession,
        source: RSSSource,
    ) -> list[NewsItem]:
        """
        使用 Semaphore 控制并发，获取单个 RSS 源

        Args:
            session: aiohttp ClientSession
            source: RSS 源配置

        Returns:
            NewsItem 列表
        """
        async with self._semaphore:
            return await self._fetch_with_retry(session, source)

    async def _fetch_with_retry(
        self,
        session: aiohttp.ClientSession,
        source: RSSSource,
    ) -> list[NewsItem]:
        """
        带重试的获取逻辑

        使用指数退避重试策略
        """
        last_exception: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                # 设置 User-Agent
                headers = {
                    "User-Agent": "AI-Insight-Tracker/1.0 (RSS Fetcher)"
                }

                async with session.get(str(source.url), headers=headers) as response:
                    response.raise_for_status()
                    content = await response.text()

                # 在线程池中执行同步解析，避免阻塞事件循环
                items = await asyncio.to_thread(parse_feed_sync, content, source)
                return items

            except asyncio.TimeoutError as e:
                last_exception = e
                wait_time = 2**attempt  # 指数退避: 1, 2, 4 秒
                logger.debug(
                    f"获取 {source.name} 超时，"
                    f"等待 {wait_time} 秒后重试 ({attempt + 1}/{self._max_retries})"
                )
                await asyncio.sleep(wait_time)

            except aiohttp.ClientError as e:
                last_exception = e
                wait_time = 2**attempt
                logger.debug(
                    f"获取 {source.name} 网络错误: {e}，"
                    f"等待 {wait_time} 秒后重试 ({attempt + 1}/{self._max_retries})"
                )
                await asyncio.sleep(wait_time)

            except Exception as e:
                # 其他错误直接抛出，不重试
                raise e

        # 所有重试都失败
        raise last_exception or RuntimeError(f"获取 {source.name} 失败")

