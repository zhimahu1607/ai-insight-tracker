"""
Google Research 博客提取器

目标页面: https://research.google/blog/
页面特点: 需要 JavaScript 渲染
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from src.models import NewsItem, NewsSource, FetchType
from ..base import BaseExtractor


class GoogleResearchExtractor(BaseExtractor):
    """Google Research 博客提取器"""

    BASE_URL = "https://research.google"

    def get_extraction_schema(self) -> dict:
        """返回 CSS 提取 Schema"""
        return {
            "name": "Google Research Blog Posts",
            "baseSelector": "article, a[href*='/blog/'], .blog-post, .post-card",
            "fields": [
                {
                    "name": "title",
                    "selector": "h2, h3, .title, span[class*='title']",
                    "type": "text",
                },
                {
                    "name": "url",
                    "selector": "a",
                    "type": "attribute",
                    "attribute": "href",
                },
                {
                    "name": "date",
                    "selector": "time, .date, span[class*='date']",
                    "type": "text",
                },
                {
                    "name": "summary",
                    "selector": "p, .description, .excerpt",
                    "type": "text",
                },
            ],
        }

    def parse_result(
        self,
        extracted_content: str,
        source: NewsSource,
    ) -> list[NewsItem]:
        """解析爬取结果"""
        items: list[NewsItem] = []

        if not extracted_content:
            return items

        try:
            articles = json.loads(extracted_content)
        except json.JSONDecodeError:
            return items

        seen_urls: set[str] = set()

        for article in articles:
            title = article.get("title", "").strip()
            url = article.get("url", "").strip()

            if not title or not url:
                continue

            # 补全相对 URL
            if url.startswith("/"):
                url = f"{self.BASE_URL}{url}"

            # 去重
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # 过滤非博客链接
            if "/blog/" not in url:
                continue

            # 解析日期
            date_str = article.get("date", "")
            published = self._parse_date(date_str)

            # 生成 ID
            item_id = hashlib.md5(url.encode()).hexdigest()[:16]

            items.append(NewsItem(
                id=item_id,
                title=title,
                url=url,
                source_name=source.name,
                source_category="ai",
                language=source.language,
                published=published,
                summary=article.get("summary"),
                weight=source.weight,
                fetch_type=FetchType.CRAWLER,
                company=source.company,
            ))

        return items

    def get_js_code(self) -> Optional[str]:
        """返回 JavaScript 代码，用于等待内容加载"""
        return """
        // 等待页面内容加载
        await new Promise(resolve => setTimeout(resolve, 3000));

        // 滚动以触发懒加载
        for (let i = 0; i < 3; i++) {
            window.scrollTo(0, document.body.scrollHeight * (i + 1) / 3);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        """

    def get_base_url(self) -> str:
        return self.BASE_URL

    def _parse_date(self, date_str: str) -> datetime:
        """解析日期字符串"""
        if not date_str:
            return datetime.now(timezone.utc)

        formats = [
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        return datetime.now(timezone.utc)

