"""
DeepSeek 新闻页面提取器

目标页面: https://api-docs.deepseek.com/zh-cn/news/
页面特点: 静态页面，不需要 JavaScript 渲染
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from src.models import NewsItem, NewsSource, FetchType
from ..base import BaseExtractor


class DeepSeekExtractor(BaseExtractor):
    """DeepSeek 新闻页面提取器"""

    BASE_URL = "https://api-docs.deepseek.com"

    def get_extraction_schema(self) -> dict:
        """返回 CSS 提取 Schema"""
        return {
            "name": "DeepSeek News",
            "baseSelector": "article, .news-item, .post, a[href*='/news/']",
            "fields": [
                {
                    "name": "title",
                    "selector": "h1, h2, h3, .title, a",
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
                    "selector": "time, .date, .meta, span",
                    "type": "text",
                },
                {
                    "name": "summary",
                    "selector": "p, .summary, .excerpt",
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
        """DeepSeek 是静态页面，不需要 JS"""
        return None

    def get_base_url(self) -> str:
        return self.BASE_URL

    def _parse_date(self, date_str: str) -> datetime:
        """解析日期字符串"""
        if not date_str:
            return datetime.now(timezone.utc)

        # 中文日期格式
        formats = [
            "%Y-%m-%d",
            "%Y年%m月%d日",
            "%Y.%m.%d",
            "%m/%d/%Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        return datetime.now(timezone.utc)

