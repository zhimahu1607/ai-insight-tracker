"""Gemini product blog extractor."""

from typing import Optional

from ..base import BaseExtractor


class GeminiExtractor(BaseExtractor):
    BASE_URL = "https://blog.google"
    DATE_FORMATS = ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y")

    def get_extraction_schema(self) -> dict:
        return {
            "name": "Gemini Blog Posts",
            "baseSelector": "article, a[href*='/products/gemini/'], .article-card, .post",
            "fields": [
                {"name": "title", "selector": "h2, h3, .title, span[class*='headline']", "type": "text"},
                {"name": "url", "selector": "a", "type": "attribute", "attribute": "href"},
                {"name": "date", "selector": "time, .date, span[class*='date']", "type": "text"},
                {"name": "summary", "selector": "p, .description, .excerpt, .summary", "type": "text"},
            ],
        }

    def should_include_url(self, url: str) -> bool:
        return "/products/gemini/" in url or "gemini" in url.lower()

    def get_js_code(self) -> Optional[str]:
        return """
        await new Promise(resolve => setTimeout(resolve, 3000));
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(resolve => setTimeout(resolve, 2000));
        """
