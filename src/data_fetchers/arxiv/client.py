"""
arXiv 异步客户端

使用 aiohttp + feedparser 异步获取 arXiv 论文数据。
采用 Semaphore 控制并发，遵守 arXiv API 限流规则。
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import aiohttp
import feedparser

from src.models import Paper
from .query import build_single_category_query, build_id_query

logger = logging.getLogger(__name__)


class AsyncArxivClient:
    """
    异步 arXiv API 客户端

    Features:
        - 使用 aiohttp 异步获取数据
        - Semaphore 控制并发，遵守限流规则
        - 指数退避重试
        - feedparser 解析 Atom XML
    """

    def __init__(
        self,
        timeout: float = 60.0,
        max_results_per_category: int = 100,
        max_pages_per_category: int = 20,
        delay_between_requests: float = 3.0,
        max_retries: int = 3,
    ):
        """
        初始化客户端

        Args:
            timeout: HTTP 请求超时（秒）
            max_results_per_category: 单次请求最大返回数（分页时为“每页大小”）
            max_pages_per_category: 每个分类最多分页次数（用于安全兜底，避免无限拉取）
            delay_between_requests: 请求间隔（秒），遵守 arXiv 限流
            max_retries: 最大重试次数
        """
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._page_size = max_results_per_category
        self._max_pages_per_category = max(1, int(max_pages_per_category))
        self._delay = delay_between_requests
        self._max_retries = max_retries
        self._last_request_time = 0.0
        self._semaphore = asyncio.Semaphore(1)  # 受控并发：每次只允许 1 个请求

    async def fetch_recent_papers(
        self,
        categories: list[str],
        hours: int = 25,
    ) -> list[Paper]:
        """
        获取指定分类的最近论文

        Args:
            categories: 分类列表，如 ["cs.AI", "cs.CL"]
            hours: 获取最近多少小时的论文，默认25小时

        Returns:
            去重后的论文列表（只保留主分类匹配的论文）
        """
        # 并发获取所有分类（Semaphore 自动控制并发数）
        tasks = [self._rate_limited_request(cat, hours=hours) for cat in categories]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_papers: list[Paper] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"获取分类 {categories[i]} 失败: {result}")
            else:
                all_papers.extend(result)

        # 按论文 ID 去重（同一篇论文可能在多个分类中出现）
        seen_ids: set[str] = set()
        unique_papers: list[Paper] = []
        for paper in all_papers:
            if paper.id not in seen_ids:
                seen_ids.add(paper.id)
                unique_papers.append(paper)

        # 只保留主分类在目标列表中的论文
        target_categories = set(categories)
        filtered_papers = [
            p for p in unique_papers if p.primary_category in target_categories
        ]

        # 客户端日期过滤（使用小时）
        filtered_papers = self._filter_by_hours(filtered_papers, hours)

        logger.info(
            f"[arXiv] 获取完成: {len(all_papers)} 篇论文, "
            f"去重后: {len(unique_papers)} 篇, "
            f"日期过滤后: {len(filtered_papers)} 篇"
        )

        return filtered_papers

    async def fetch_by_ids(self, paper_ids: list[str]) -> list[Paper]:
        """
        按论文 ID 批量获取

        Args:
            paper_ids: 论文 ID 列表，如 ["2501.12345", "2501.12346"]

        Returns:
            论文列表
        """
        if not paper_ids:
            return []

        url = build_id_query(paper_ids)
        return await self._fetch_and_parse(url)

    async def _rate_limited_request(self, category: str, hours: int = 25) -> list[Paper]:
        """
        受控并发请求：Semaphore 确保同一时刻只有一个请求
        """
        async with self._semaphore:
            # 等待请求间隔
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._delay:
                await asyncio.sleep(self._delay - elapsed)

            # 执行请求
            result = await self._fetch_category_paginated(category, hours=hours)
            self._last_request_time = time.time()
            return result

    def _latest_time(self, paper: Paper) -> datetime:
        """
        获取论文的“最新时间”

        使用 published 和 updated 中较新的日期，用于：
        - 和 hours 时间窗口对齐
        - 分页时判断是否可以提前停止
        """
        pub_time = paper.published
        if pub_time.tzinfo is None:
            pub_time = pub_time.replace(tzinfo=timezone.utc)

        upd_time = None
        if paper.updated:
            upd_time = paper.updated
            if upd_time.tzinfo is None:
                upd_time = upd_time.replace(tzinfo=timezone.utc)

        return max(pub_time, upd_time) if upd_time else pub_time

    async def _fetch_category_paginated(self, category: str, hours: int = 25) -> list[Paper]:
        """
        获取单个分类的论文（支持分页）

        规则：
        - 每页大小 = self._page_size（通常 100）
        - start = 0, 100, 200... 递增
        - 如果某一页返回数量 < page_size，表示已无更多结果 → 停止
        - 如果某一页“最旧”的论文已经早于 cutoff，后续页只会更旧 → 提前停止
        - 额外使用 max_pages_per_category 作为安全上限
        """
        collected: list[Paper] = []

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)

        start = 0
        for page_idx in range(self._max_pages_per_category):
            url = build_single_category_query(
                category=category,
                max_results=self._page_size,
                start=start,
            )

            page_papers = await self._fetch_and_parse(url)
            if not page_papers:
                break

            collected.extend(page_papers)

            # 如果这一页不足 page_size，说明后面没有更多
            if len(page_papers) < self._page_size:
                break

            # 基于时间窗口提前停止：这一页最旧的论文都早于 cutoff，则下一页只会更旧
            try:
                oldest_in_page = self._latest_time(page_papers[-1])
                if oldest_in_page < cutoff:
                    break
            except Exception:
                # 解析异常不影响整体流程，继续分页（由 max_pages 兜底）
                pass

            start += self._page_size

        if collected and len(collected) >= self._page_size:
            logger.info(
                f"[arXiv] 分类 {category} 分页获取: 共 {len(collected)} 篇 "
                f"(page_size={self._page_size}, max_pages={self._max_pages_per_category})"
            )

        return collected

    async def _fetch_and_parse(self, url: str) -> list[Paper]:
        """
        获取并解析 arXiv API 响应

        使用指数退避重试策略
        """
        last_exception: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self._timeout) as session:
                    # 设置 User-Agent
                    headers = {
                        "User-Agent": "AI-Insight-Tracker/1.0 (https://github.com/)"
                    }
                    async with session.get(url, headers=headers) as response:
                        # 处理限流
                        if response.status == 429:
                            wait_time = 30
                            logger.warning(
                                f"arXiv API 限流 (429)，等待 {wait_time} 秒后重试"
                            )
                            await asyncio.sleep(wait_time)
                            continue

                        # 处理服务器错误
                        if response.status >= 500:
                            wait_time = 2**attempt  # 指数退避: 1, 2, 4 秒
                            logger.warning(
                                f"arXiv API 错误 ({response.status})，"
                                f"等待 {wait_time} 秒后重试"
                            )
                            await asyncio.sleep(wait_time)
                            continue

                        response.raise_for_status()
                        content = await response.text()

                # 在线程池中执行同步解析，避免阻塞事件循环
                papers = await asyncio.to_thread(self._parse_response, content)
                return papers

            except asyncio.TimeoutError as e:
                last_exception = e
                wait_time = 2**attempt
                logger.warning(f"请求超时，等待 {wait_time} 秒后重试 ({attempt + 1}/{self._max_retries})")
                await asyncio.sleep(wait_time)

            except aiohttp.ClientError as e:
                last_exception = e
                wait_time = 2**attempt
                logger.warning(f"网络错误: {e}，等待 {wait_time} 秒后重试 ({attempt + 1}/{self._max_retries})")
                await asyncio.sleep(wait_time)

        # 所有重试都失败
        raise last_exception or RuntimeError("未知错误")

    def _parse_response(self, content: str) -> list[Paper]:
        """
        解析 arXiv Atom XML 响应

        此方法是同步的，由 asyncio.to_thread() 在线程池中执行
        """
        feed = feedparser.parse(content)
        papers: list[Paper] = []

        for entry in feed.entries:
            try:
                paper = self._entry_to_paper(entry)
                papers.append(paper)
            except Exception as e:
                logger.warning(f"解析论文条目失败: {e}")
                continue

        return papers

    def _entry_to_paper(self, entry: Any) -> Paper:
        """
        将 feedparser entry 转换为 Paper 对象
        """
        # 提取 arXiv ID（从 URL 中提取）
        arxiv_id = self._extract_arxiv_id(entry.id)

        # 解析作者列表
        authors = [author.name for author in entry.get("authors", [])]

        # 解析分类
        categories = [tag.term for tag in entry.get("tags", [])]
        primary_category = getattr(
            entry, "arxiv_primary_category", {}
        ).get("term", categories[0] if categories else "")

        # 解析时间
        published = self._parse_datetime(entry.get("published", ""))
        updated = self._parse_datetime(entry.get("updated", ""))

        # 构建 URL
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        # 获取作者备注（可能不存在）
        comment = getattr(entry, "arxiv_comment", None)

        return Paper(
            id=arxiv_id,
            title=entry.title.replace("\n", " ").strip(),
            authors=authors,
            abstract=entry.summary.replace("\n", " ").strip(),
            categories=categories,
            primary_category=primary_category,
            pdf_url=pdf_url,
            abs_url=abs_url,
            published=published,
            updated=updated if updated else None,
            comment=comment,
        )

    def _extract_arxiv_id(self, entry_id: str) -> str:
        """
        从 entry.id URL 提取论文 ID

        entry.id 格式: http://arxiv.org/abs/2501.12345v1
        需要提取: 2501.12345
        """
        # 移除 URL 前缀和版本号
        arxiv_id = entry_id.split("/")[-1]  # 2501.12345v1
        # 移除版本号
        if "v" in arxiv_id:
            arxiv_id = arxiv_id.split("v")[0]  # 2501.12345
        return arxiv_id

    def _parse_datetime(self, date_str: str) -> datetime:
        """解析 ISO 8601 格式日期"""
        if not date_str:
            return datetime.now(timezone.utc)
        try:
            # feedparser 返回的时间元组
            from dateutil import parser
            return parser.parse(date_str)
        except Exception:
            return datetime.now(timezone.utc)

    def _filter_by_hours(self, papers: list[Paper], hours: int = 25) -> list[Paper]:
        """
        过滤指定小时数内的论文

        使用 published 和 updated 中较新的日期进行过滤。
        这样可以同时保留：
        - 新发布的论文（published 在时间窗口内）
        - 最近更新的论文（updated 在时间窗口内）

        Args:
            papers: 论文列表
            hours: 时间窗口（小时），默认25小时

        Returns:
            时间窗口内的论文列表
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        
        # 调试日志：输出前3篇论文的时间信息
        if papers:
            logger.debug(f"[arXiv] 当前 UTC 时间: {now.isoformat()}")
            logger.debug(f"[arXiv] 截止时间 (cutoff): {cutoff.isoformat()}")
            for i, p in enumerate(papers[:3]):
                pub_info = f"published={p.published.isoformat() if p.published else 'None'}"
                upd_info = f"updated={p.updated.isoformat() if p.updated else 'None'}"
                logger.debug(f"[arXiv] 论文[{i}] {p.id}: {pub_info}, {upd_info}")
        
        filtered = []
        for p in papers:
            # 获取 published 时间（确保有时区信息）
            pub_time = p.published
            if pub_time.tzinfo is None:
                pub_time = pub_time.replace(tzinfo=timezone.utc)
            
            # 获取 updated 时间（如果存在）
            upd_time = None
            if p.updated:
                upd_time = p.updated
                if upd_time.tzinfo is None:
                    upd_time = upd_time.replace(tzinfo=timezone.utc)
            
            # 使用较新的时间进行过滤
            latest_time = max(pub_time, upd_time) if upd_time else pub_time
            if latest_time >= cutoff:
                filtered.append(p)
        
        # 如果过滤后为空，输出更多调试信息
        if not filtered and papers:
            # 找出最近的论文时间
            latest_paper_times = []
            for p in papers[:10]:
                pub_time = p.published
                if pub_time.tzinfo is None:
                    pub_time = pub_time.replace(tzinfo=timezone.utc)
                upd_time = None
                if p.updated:
                    upd_time = p.updated
                    if upd_time.tzinfo is None:
                        upd_time = upd_time.replace(tzinfo=timezone.utc)
                latest = max(pub_time, upd_time) if upd_time else pub_time
                latest_paper_times.append((p.id, latest))
            
            latest_paper_times.sort(key=lambda x: x[1], reverse=True)
            logger.warning(
                f"[arXiv] 日期过滤后无论文！前5篇最新论文时间: "
                f"{[(pid, t.isoformat()) for pid, t in latest_paper_times[:5]]}"
            )
            logger.warning(f"[arXiv] 时间窗口: {cutoff.isoformat()} ~ {now.isoformat()}")
        
        return filtered

