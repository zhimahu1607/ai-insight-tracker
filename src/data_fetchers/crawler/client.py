"""
异步 Web 爬虫客户端

基于 crawl4ai 实现，用于获取无 RSS 源的公司博客。
"""

import asyncio
import logging
from typing import Optional

from src.models import NewsItem, NewsSource, FetchType

logger = logging.getLogger(__name__)

# 尝试导入 crawl4ai，如果不可用则提供降级方案
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
    from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning(
        "crawl4ai 未安装，Crawler 功能不可用。"
        "请运行: pip install crawl4ai && playwright install chromium"
    )


class AsyncNewsCrawler:
    """
    异步新闻爬虫

    Features:
        - 基于 crawl4ai 的异步爬取
        - 支持 JavaScript 渲染
        - 每个网站使用专用提取器
        - Semaphore 控制并发
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        timeout: float = 60.0,
        headless: bool = True,
    ):
        """
        初始化爬虫

        Args:
            max_concurrent: 最大并发爬取数（浏览器实例数）
            timeout: 页面加载超时（秒）
            headless: 是否使用无头模式
        """
        self._max_concurrent = max_concurrent
        self._timeout = timeout
        self._headless = headless
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_all(
        self,
        sources: list[NewsSource],
    ) -> list[NewsItem]:
        """
        并发爬取所有源

        Args:
            sources: 新闻源配置列表

        Returns:
            NewsItem 列表
        """
        # 检查 crawl4ai 是否可用
        if not CRAWL4AI_AVAILABLE:
            logger.error("crawl4ai 未安装，无法执行爬取")
            return []

        # 过滤出需要爬取的源
        crawler_sources = [
            s for s in sources
            if s.fetch_type == FetchType.CRAWLER and s.enabled
        ]

        if not crawler_sources:
            logger.info("没有需要爬取的源")
            return []

        logger.info(f"开始爬取 {len(crawler_sources)} 个新闻源")

        # 配置浏览器
        browser_config = BrowserConfig(
            headless=self._headless,
            verbose=False,
        )

        all_items: list[NewsItem] = []

        async with AsyncWebCrawler(config=browser_config) as crawler:
            tasks = [
                self._fetch_source(crawler, source)
                for source in crawler_sources
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(
                        f"爬取 {crawler_sources[i].name} 失败: {result}"
                    )
                else:
                    all_items.extend(result)

        logger.info(f"爬取完成，共 {len(all_items)} 条新闻")
        return all_items

    async def _fetch_source(
        self,
        crawler,  # AsyncWebCrawler
        source: NewsSource,
    ) -> list[NewsItem]:
        """
        使用 Semaphore 控制并发，爬取单个源
        """
        async with self._semaphore:
            return await self._fetch_with_extractor(crawler, source)

    async def _fetch_with_extractor(
        self,
        crawler,  # AsyncWebCrawler
        source: NewsSource,
    ) -> list[NewsItem]:
        """
        使用专用提取器爬取单个源
        """
        from .extractors import get_extractor

        # 获取该网站的专用提取器
        try:
            extractor = get_extractor(source.extractor or source.company)
        except ValueError as e:
            logger.error(f"获取提取器失败: {e}")
            return []

        # 构建提取策略
        extraction_strategy = JsonCssExtractionStrategy(
            schema=extractor.get_extraction_schema()
        )

        # 配置爬取参数
        run_config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy,
            wait_until="networkidle",
            page_timeout=int(self._timeout * 1000),
        )

        # 如果需要执行 JS
        js_code = extractor.get_js_code() if source.js_render else None
        if js_code:
            run_config.js_code = js_code

        logger.debug(f"开始爬取: {source.name} ({source.blog_url})")

        # 执行爬取
        try:
            result = await crawler.arun(
                url=str(source.blog_url),
                config=run_config,
            )
        except Exception as e:
            logger.error(f"爬取 {source.name} 出错: {e}")
            raise

        if not result.success:
            error_msg = getattr(result, 'error_message', 'Unknown error')
            raise RuntimeError(f"爬取失败: {error_msg}")

        # 解析结果
        extracted_content = result.extracted_content or ""
        items = extractor.parse_result(extracted_content, source)

        logger.debug(f"从 {source.name} 获取 {len(items)} 条新闻")
        return items


async def fetch_with_crawler(
    sources: list[NewsSource],
    max_concurrent: int = 3,
    timeout: float = 60.0,
) -> list[NewsItem]:
    """
    便捷函数：使用爬虫获取新闻

    Args:
        sources: 新闻源配置列表
        max_concurrent: 最大并发数
        timeout: 超时时间

    Returns:
        NewsItem 列表
    """
    crawler = AsyncNewsCrawler(
        max_concurrent=max_concurrent,
        timeout=timeout,
    )
    return await crawler.fetch_all(sources)

