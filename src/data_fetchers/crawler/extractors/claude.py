"""
Claude 博客提取器

目标页面: https://claude.com/blog
页面特点: 可能需要 JavaScript 渲染
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from src.models import NewsItem, NewsSource, FetchType
from src.data_fetchers.text_utils import clean_html_to_text
from ..base import BaseExtractor


class ClaudeExtractor(BaseExtractor):
    """Claude 博客提取器（同 Anthropic 公司聚合）"""

    BASE_URL = "https://claude.com"

    def get_extraction_schema(self) -> dict:
        return {
            "name": "Claude Blog Posts",
            "baseSelector": "a[href^='/blog/'], article, .post, .post-card",
            "fields": [
                {"name": "title", "selector": "h2, h3, .title, span", "type": "text"},
                {"name": "url", "type": "attribute", "attribute": "href"},
                {"name": "date", "selector": "time, .date, span[class*='date']", "type": "text"},
                {"name": "summary", "selector": "p, .description, .excerpt", "type": "text"},
            ],
        }

    def get_detail_extraction_schema(self) -> Optional[dict]:
        return {
            "name": "Claude Blog Detail",
            "baseSelector": "main, article",
            "fields": [
                {"name": "title", "selector": "h1", "type": "text"},
                {"name": "date", "selector": "time, .date", "type": "text"},
                {"name": "content", "selector": "main, article", "type": "text"},
            ],
        }

    def parse_detail_result(
        self,
        extracted_content: str,
        source: NewsSource,
    ) -> Optional[str]:
        _ = source
        if not extracted_content:
            return None
        try:
            data = json.loads(extracted_content)
        except json.JSONDecodeError:
            return None

        if isinstance(data, list) and data:
            content = data[0].get("content")
            return clean_html_to_text(str(content)) if content else None
        if isinstance(data, dict):
            content = data.get("content")
            return clean_html_to_text(str(content)) if content else None
        return None

    def parse_result(
        self,
        extracted_content: str,
        source: NewsSource,
    ) -> list[NewsItem]:
        items: list[NewsItem] = []
        if not extracted_content:
            return items

        try:
            articles = json.loads(extracted_content)
        except json.JSONDecodeError:
            return items

        seen_urls: set[str] = set()

        for article in articles:
            title = (article.get("title") or "").strip()
            url = (article.get("url") or "").strip()
            if not title or not url:
                continue

            if url.startswith("/"):
                url = f"{self.BASE_URL}{url}"

            if "/blog/" not in url:
                continue

            if url in seen_urls:
                continue
            seen_urls.add(url)

            date_str = (article.get("date") or "").strip()
            published = self._parse_date(date_str)

            item_id = hashlib.md5(url.encode()).hexdigest()[:16]
            items.append(
                NewsItem(
                    id=item_id,
                    title=title,
                    url=url,
                    source_name=source.name,
                    source_category="ai",
                    language=source.language,
                    published=published,
                    summary=(article.get("summary") or None),
                    content=None,  # 详情页补全
                    weight=source.weight,
                    fetch_type=FetchType.CRAWLER,
                    company=source.company,
                )
            )

        return items

    def get_js_code(self) -> Optional[str]:
        return """
        // 等待页面内容加载
        await new Promise(resolve => setTimeout(resolve, 2000));
        window.scrollTo(0, document.body.scrollHeight / 2);
        await new Promise(resolve => setTimeout(resolve, 1000));
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(resolve => setTimeout(resolve, 1000));
        """

    def get_detail_js_code(self) -> Optional[str]:
        # 详情页同样等待渲染
        return self.get_js_code()

    def get_base_url(self) -> str:
        return self.BASE_URL

    def _parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.now(timezone.utc)
        formats = [
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return datetime.now(timezone.utc)


