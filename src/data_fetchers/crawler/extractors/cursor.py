"""
Cursor 博客提取器

目标页面:
- https://cursor.com/cn/blog (中文)
- https://cursor.com/blog (英文)

说明：目前项目按单个 source 的 blog_url 抓取；如需中英都抓，可配置两个 source。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from src.models import NewsItem, NewsSource, FetchType
from src.data_fetchers.text_utils import clean_html_to_text
from ..base import BaseExtractor


class CursorExtractor(BaseExtractor):
    """Cursor 博客提取器"""

    BASE_URL = "https://cursor.com"

    def get_extraction_schema(self) -> dict:
        # 列表页：尽量覆盖常见结构（a 卡片 / article）
        return {
            "name": "Cursor Blog Posts",
            "baseSelector": "a[href*='/blog/'], a[href*='/cn/blog/'], article, .post, .card",
            "fields": [
                {"name": "title", "selector": "h2, h3, .title, span", "type": "text"},
                {"name": "url", "type": "attribute", "attribute": "href"},
                {"name": "date", "selector": "time, .date, span[class*='date']", "type": "text"},
                {"name": "summary", "selector": "p, .description, .excerpt", "type": "text"},
            ],
        }

    def get_detail_extraction_schema(self) -> Optional[dict]:
        return {
            "name": "Cursor Blog Detail",
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

            # 过滤非博客文章
            if "/blog/" not in url and "/cn/blog/" not in url:
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
        // 滚动触发懒加载
        for (let i = 0; i < 3; i++) {
            window.scrollTo(0, document.body.scrollHeight * (i + 1) / 3);
            await new Promise(resolve => setTimeout(resolve, 800));
        }
        """

    def get_detail_js_code(self) -> Optional[str]:
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


