"""Anthropic research page extractor."""

from typing import Optional

from ..base import BaseExtractor


class AnthropicExtractor(BaseExtractor):
    BASE_URL = "https://www.anthropic.com"
    DATE_FORMATS = BaseExtractor.DATE_FORMATS + ("%b %Y", "%B %Y")

    def get_extraction_schema(self) -> dict:
        return {
            "name": "Anthropic Research Articles",
            "baseSelector": "a[href*='/research/']",
            "fields": [
                {"name": "title", "selector": "h3, h2, .title, span", "type": "text"},
                {"name": "url", "type": "attribute", "attribute": "href"},
                {"name": "date", "selector": "time, .date, span[class*='date']", "type": "text"},
                {"name": "summary", "selector": "p, .description, .excerpt", "type": "text"},
            ],
        }

    def get_detail_extraction_schema(self) -> Optional[dict]:
        return {
            "name": "Anthropic Research Detail",
            "baseSelector": "main, article",
            "fields": [
                {"name": "title", "selector": "h1", "type": "text"},
                {"name": "date", "selector": "time, .date", "type": "text"},
                {"name": "content", "selector": "main, article", "type": "text"},
            ],
        }

    def should_include_url(self, url: str) -> bool:
        return "/research/" in url

    def get_js_code(self) -> Optional[str]:
        return """
        await new Promise(resolve => setTimeout(resolve, 2000));
        window.scrollTo(0, document.body.scrollHeight / 2);
        await new Promise(resolve => setTimeout(resolve, 1000));
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(resolve => setTimeout(resolve, 1000));
        """
