"""DeepMind blog extractor."""

from typing import Optional

from ..base import BaseExtractor


class DeepMindExtractor(BaseExtractor):
    BASE_URL = "https://deepmind.google"

    def get_extraction_schema(self) -> dict:
        return {
            "name": "DeepMind Blog Posts",
            "baseSelector": "article, a[href*='/discover/blog/'], .blog-card, .post-card",
            "fields": [
                {"name": "title", "selector": "h2, h3, .title, span[class*='title']", "type": "text"},
                {"name": "url", "selector": "a", "type": "attribute", "attribute": "href"},
                {"name": "date", "selector": "time, .date, span[class*='date']", "type": "text"},
                {"name": "summary", "selector": "p, .description, .excerpt", "type": "text"},
            ],
        }

    def should_include_url(self, url: str) -> bool:
        return "/discover/blog/" in url or "/blog/" in url

    def get_js_code(self) -> Optional[str]:
        return """
        await new Promise(resolve => setTimeout(resolve, 3000));
        for (let i = 0; i < 3; i++) {
            window.scrollTo(0, document.body.scrollHeight * (i + 1) / 3);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        """
