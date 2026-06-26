"""DeepSeek news page extractor."""

from typing import Optional

from ..base import BaseExtractor


class DeepSeekExtractor(BaseExtractor):
    BASE_URL = "https://api-docs.deepseek.com"
    DATE_FORMATS = ("%Y-%m-%d", "%Y年%m月%d日", "%Y.%m.%d", "%m/%d/%Y")

    def get_extraction_schema(self) -> dict:
        return {
            "name": "DeepSeek News",
            "baseSelector": "article, .news-item, .post, a[href*='/news/']",
            "fields": [
                {"name": "title", "selector": "h1, h2, h3, .title, a", "type": "text"},
                {"name": "url", "selector": "a", "type": "attribute", "attribute": "href"},
                {"name": "date", "selector": "time, .date, .meta, span", "type": "text"},
                {"name": "summary", "selector": "p, .summary, .excerpt", "type": "text"},
            ],
        }

    def get_js_code(self) -> Optional[str]:
        return None
