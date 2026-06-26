"""Qwen research page extractor."""

from typing import Optional

from ..base import BaseExtractor


class QwenExtractor(BaseExtractor):
    BASE_URL = "https://qwen.ai"
    DATE_FORMATS = ("%Y-%m-%d", "%Y年%m月%d日", "%B %d, %Y", "%b %d, %Y", "%Y.%m.%d")

    def get_extraction_schema(self) -> dict:
        return {
            "name": "Qwen Research Posts",
            "baseSelector": "article, a[href*='/blog/'], .research-card, .post-card, div[class*='card']",
            "fields": [
                {"name": "title", "selector": "h2, h3, .title, span[class*='title']", "type": "text"},
                {"name": "url", "selector": "a", "type": "attribute", "attribute": "href"},
                {"name": "date", "selector": "time, .date, span[class*='date']", "type": "text"},
                {"name": "summary", "selector": "p, .description, .excerpt", "type": "text"},
            ],
        }

    def get_js_code(self) -> Optional[str]:
        return """
        await new Promise(resolve => setTimeout(resolve, 3000));
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(resolve => setTimeout(resolve, 2000));
        """
