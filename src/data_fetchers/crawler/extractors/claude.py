"""Claude blog extractor."""

from __future__ import annotations

from typing import Optional

from ..base import BaseExtractor


class ClaudeExtractor(BaseExtractor):
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

    def should_include_url(self, url: str) -> bool:
        return "/blog/" in url

    def get_js_code(self) -> Optional[str]:
        return """
        await new Promise(resolve => setTimeout(resolve, 2000));
        window.scrollTo(0, document.body.scrollHeight / 2);
        await new Promise(resolve => setTimeout(resolve, 1000));
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(resolve => setTimeout(resolve, 1000));
        """

    def get_detail_js_code(self) -> Optional[str]:
        return self.get_js_code()
