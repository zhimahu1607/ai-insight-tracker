"""
网络搜索工具

支持 Tavily (首选) 和 DuckDuckGo (备选) 两种搜索后端。
根据配置自动选择，实现无缝降级。
"""

import asyncio
import logging
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.config import get_settings


logger = logging.getLogger(__name__)


class SearchInput(BaseModel):
    """搜索工具输入"""

    queries: list[str] = Field(
        description="搜索查询列表，每个查询是一个搜索关键词或问题"
    )


async def _search_with_tavily(
    queries: list[str],
    max_results: int = 5,
    timeout: int = 30,
) -> list[dict]:
    """
    使用 Tavily API 执行搜索

    Args:
        queries: 搜索查询列表
        max_results: 每个查询返回的最大结果数
        timeout: 请求超时(秒)

    Returns:
        搜索结果列表，每个结果包含 title, url, content
    """
    try:
        from tavily import AsyncTavilyClient
    except ImportError:
        raise ImportError("请安装 tavily-python: pip install tavily-python")

    settings = get_settings()
    api_key = settings.search.tavily_api_key

    if not api_key:
        raise ValueError("Tavily API Key 未配置")

    client = AsyncTavilyClient(api_key=api_key)
    results = []

    # 并发执行搜索（最多 3 个并发）
    semaphore = asyncio.Semaphore(3)

    async def search_one(query: str) -> list[dict]:
        async with semaphore:
            try:
                response = await asyncio.wait_for(
                    client.search(
                        query=query,
                        max_results=max_results,
                        search_depth="advanced",
                    ),
                    timeout=timeout,
                )
                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", ""),
                    }
                    for r in response.get("results", [])
                ]
            except asyncio.TimeoutError:
                logger.warning(f"Tavily 搜索超时 [{query}]")
                return []
            except Exception as e:
                logger.warning(f"Tavily 搜索失败 [{query}]: {e}")
                return []

    tasks = [search_one(q) for q in queries]
    all_results = await asyncio.gather(*tasks)

    for res_list in all_results:
        results.extend(res_list)

    return results


async def _search_with_duckduckgo(
    queries: list[str],
    max_results: int = 5,
) -> list[dict]:
    """
    使用 DuckDuckGo 执行搜索 (备选方案)

    Args:
        queries: 搜索查询列表
        max_results: 每个查询返回的最大结果数

    Returns:
        搜索结果列表，每个结果包含 title, url, content
    """
    try:
        from duckduckgo_search import AsyncDDGS
    except ImportError:
        raise ImportError("请安装 duckduckgo-search: pip install duckduckgo-search")

    results = []

    async with AsyncDDGS() as ddgs:
        for query in queries:
            try:
                search_results = await ddgs.atext(query, max_results=max_results)
                for r in search_results:
                    results.append(
                        {
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "content": r.get("body", ""),
                        }
                    )
            except Exception as e:
                logger.warning(f"DuckDuckGo 搜索失败 [{query}]: {e}")

    return results


async def search_web(
    queries: list[str],
    max_results: Optional[int] = None,
) -> str:
    """
    执行网络搜索

    根据配置自动选择搜索后端：
    - 如果配置了 Tavily API Key，使用 Tavily
    - 否则使用 DuckDuckGo

    Args:
        queries: 搜索查询列表
        max_results: 每个查询返回的最大结果数，默认从配置读取

    Returns:
        格式化的搜索结果字符串
    """
    settings = get_settings()
    max_results = max_results or settings.search.max_results
    timeout = settings.search.timeout

    # 选择搜索后端
    if settings.search.tavily_api_key:
        logger.info(f"使用 Tavily 搜索: {queries}")
        try:
            results = await _search_with_tavily(queries, max_results, timeout)
        except Exception as e:
            logger.warning(f"Tavily 搜索失败，降级到 DuckDuckGo: {e}")
            results = await _search_with_duckduckgo(queries, max_results)
    else:
        logger.info(f"使用 DuckDuckGo 搜索: {queries}")
        results = await _search_with_duckduckgo(queries, max_results)

    if not results:
        return "未找到相关搜索结果"

    # 格式化结果
    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(
            f"[{i}] {r['title']}\n"
            f"    URL: {r['url']}\n"
            f"    摘要: {r['content'][:300]}..."
            if len(r["content"]) > 300
            else f"[{i}] {r['title']}\n"
            f"    URL: {r['url']}\n"
            f"    摘要: {r['content']}"
        )

    return "\n\n".join(formatted)


def get_search_tool():
    """
    获取 LangChain 工具实例

    Returns:
        绑定了搜索功能的 LangChain Tool
    """

    @tool(args_schema=SearchInput)
    async def web_search(queries: list[str]) -> str:
        """
        搜索网络获取相关信息。

        用于查找：
        - 论文相关的补充资料
        - 相关工作和对比方法
        - 应用案例和实际部署
        - 社区讨论和评价

        Args:
            queries: 搜索查询列表，建议 1-3 个精确的搜索词

        Returns:
            格式化的搜索结果
        """
        return await search_web(queries)

    return web_search
