"""
异步 Web 爬虫客户端

基于 crawl4ai 实现，用于获取无 RSS 源的公司博客。
"""

import asyncio
import logging
from typing import Optional

from src.models import NewsItem, NewsSource, FetchType
from src.data_fetchers.text_utils import clean_html_to_text

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
        # 详情页抓取使用独立 semaphore，避免与 source 级别 semaphore 嵌套死锁
        self._detail_semaphore = asyncio.Semaphore(max_concurrent)

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
            # 部分站点会持续有网络活动（analytics/stream），使用 networkidle 容易超时
            wait_until="domcontentloaded",
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

        # 逐篇抓取详情页正文（如果提取器支持）
        detail_schema = extractor.get_detail_extraction_schema()
        if detail_schema and items:
            items = await self._enrich_items_with_content(
                crawler=crawler,
                source=source,
                extractor=extractor,
                items=items,
                max_items=10,  # 默认每个源只抓最新 10 条，控制成本
            )

        logger.debug(f"从 {source.name} 获取 {len(items)} 条新闻")
        return items

    async def _enrich_items_with_content(
        self,
        crawler,  # AsyncWebCrawler
        source: NewsSource,
        extractor,
        items: list[NewsItem],
        max_items: int = 10,
    ) -> list[NewsItem]:
        """
        对列表页抓到的 NewsItem 逐篇抓取详情页正文，写入 item.content
        """
        if max_items <= 0:
            return items

        # 只对前 max_items 条做详情抓取
        target_items = items[:max_items]

        async def _fetch_one(item: NewsItem) -> None:
            async with self._detail_semaphore:
                try:
                    content = await self._fetch_detail_content(
                        crawler=crawler,
                        source=source,
                        extractor=extractor,
                        url=str(item.url),
                    )
                    if content:
                        item.content = content
                except Exception as e:
                    logger.debug(f"抓取详情页失败: {item.url} - {e}")

        await asyncio.gather(*[_fetch_one(it) for it in target_items])
        return items

    async def _fetch_detail_content(
        self,
        crawler,  # AsyncWebCrawler
        source: NewsSource,
        extractor,
        url: str,
    ) -> Optional[str]:
        """
        抓取单个详情页并返回正文文本
        """
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
        from crawl4ai import CrawlerRunConfig

        schema = extractor.get_detail_extraction_schema()
        if not schema:
            return None

        extraction_strategy = JsonCssExtractionStrategy(schema=schema)
        run_config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy,
            # 详情页同样避免 networkidle 超时
            wait_until="domcontentloaded",
            page_timeout=int(self._timeout * 1000),
        )

        js_code = extractor.get_detail_js_code() if source.js_render else None
        if js_code:
            run_config.js_code = js_code

        result = await crawler.arun(url=url, config=run_config)
        if not result.success:
            return None

        extracted = result.extracted_content or ""
        content = extractor.parse_detail_result(extracted, source)
        return clean_html_to_text(content) if content else None


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

