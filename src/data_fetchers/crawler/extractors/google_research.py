"""Google Research blog extractor."""

from typing import Optional

from ..base import BaseExtractor


class GoogleResearchExtractor(BaseExtractor):
    BASE_URL = "https://research.google"
    DATE_FORMATS = ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y")

    def get_extraction_schema(self) -> dict:
        return {
            "name": "Google Research Blog Posts",
            "baseSelector": "article, a[href*='/blog/'], .blog-post, .post-card",
            "fields": [
                {"name": "title", "selector": "h2, h3, .title, span[class*='title']", "type": "text"},
                {"name": "url", "selector": "a", "type": "attribute", "attribute": "href"},
                {"name": "date", "selector": "time, .date, span[class*='date']", "type": "text"},
                {"name": "summary", "selector": "p, .description, .excerpt", "type": "text"},
            ],
        }

    def should_include_url(self, url: str) -> bool:
        return "/blog/" in url

    def get_js_code(self) -> Optional[str]:
        return """
        await new Promise(resolve => setTimeout(resolve, 3000));
        for (let i = 0; i < 3; i++) {
            window.scrollTo(0, document.body.scrollHeight * (i + 1) / 3);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        """
