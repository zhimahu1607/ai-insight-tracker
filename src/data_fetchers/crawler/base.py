"""Base classes for crawler extractors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Optional

from src.data_fetchers.text_utils import clean_html_to_text
from src.models import FetchType, NewsItem, NewsSource


@dataclass(frozen=True)
class DetailPageFields:
    title: Optional[str] = None
    content: Optional[str] = None
    date: Optional[str] = None


class BaseExtractor(ABC):
    """Shared crawler extraction behavior."""

    BASE_URL = ""
    DATE_FORMATS: tuple[str, ...] = (
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    )

    @abstractmethod
    def get_extraction_schema(self) -> dict:
        """Return a crawl4ai JsonCssExtractionStrategy schema."""
        raise NotImplementedError

    def parse_result(
        self,
        extracted_content: str,
        source: NewsSource,
    ) -> list[NewsItem]:
        records = self._load_records(extracted_content)
        if not records:
            return []

        items: list[NewsItem] = []
        seen_urls: set[str] = set()

        for record in records:
            title = str(record.get("title") or "").strip()
            url = self._normalize_url(str(record.get("url") or "").strip())
            if not title or not url or not self.should_include_url(url):
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            items.append(
                NewsItem(
                    id=hashlib.md5(url.encode()).hexdigest()[:16],
                    title=title,
                    url=url,
                    source_name=source.name,
                    source_category="ai",
                    language=source.language,
                    published=self._parse_date(str(record.get("date") or "")),
                    summary=record.get("summary") or None,
                    content=None,
                    weight=source.weight,
                    fetch_type=FetchType.CRAWLER,
                    company=source.company,
                )
            )

        return items

    def should_include_url(self, url: str) -> bool:
        return True

    def _normalize_url(self, url: str) -> str:
        if url.startswith("/") and self.BASE_URL:
            return f"{self.BASE_URL}{url}"
        return url

    def _load_records(self, extracted_content: str) -> list[dict[str, Any]]:
        if not extracted_content:
            return []
        try:
            data = json.loads(extracted_content)
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]
        return []

    def _parse_date(self, date_str: str) -> datetime:
        date_str = date_str.strip()
        if not date_str:
            return datetime.now(timezone.utc)

        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return datetime.now(timezone.utc)

    def get_detail_extraction_schema(self) -> Optional[dict]:
        return None

    def parse_detail_result(
        self,
        extracted_content: str,
        source: NewsSource,
    ) -> Optional[str]:
        fields = self.parse_detail_fields(extracted_content, source)
        return fields.content if fields else None

    def parse_detail_fields(
        self,
        extracted_content: str,
        source: NewsSource,
    ) -> Optional[DetailPageFields]:
        _ = source
        records = self._load_records(extracted_content)
        if not records:
            return None

        record = records[0]
        raw_title = record.get("title")
        raw_content = record.get("content")
        raw_date = record.get("date")

        title = clean_html_to_text(str(raw_title)).strip() if raw_title else None
        content = clean_html_to_text(str(raw_content)) if raw_content else None
        date = clean_html_to_text(str(raw_date)).strip() if raw_date else None

        if not title and not content and not date:
            return None

        return DetailPageFields(title=title or None, content=content or None, date=date or None)

    def get_detail_js_code(self) -> Optional[str]:
        return None

    def get_js_code(self) -> Optional[str]:
        return None
