"""Semantic Scholar quality signals."""

import logging
from collections.abc import Iterable
from typing import Any

import aiohttp

from src.models import Paper, SemanticScholarSignal


logger = logging.getLogger(__name__)

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
FIELDS = ",".join(
    [
        "paperId",
        "citationCount",
        "influentialCitationCount",
        "referenceCount",
        "venue",
        "publicationTypes",
        "fieldsOfStudy",
        "s2FieldsOfStudy",
        "tldr",
    ]
)


def _chunks(items: list[Paper], size: int) -> Iterable[list[Paper]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _extract_fields_of_study(raw: dict[str, Any]) -> list[str]:
    fields: set[str] = set()
    for item in raw.get("fieldsOfStudy") or []:
        if isinstance(item, str):
            fields.add(item)
    for item in raw.get("s2FieldsOfStudy") or []:
        if isinstance(item, dict) and item.get("category"):
            fields.add(str(item["category"]))
    return sorted(fields)


def _extract_tldr(raw: dict[str, Any]) -> str | None:
    tldr = raw.get("tldr")
    if isinstance(tldr, dict):
        text = tldr.get("text")
        return str(text) if text else None
    return None


async def fetch_semantic_scholar_signals(
    session: aiohttp.ClientSession,
    papers: list[Paper],
    *,
    api_key: str = "",
    timeout: float = 20.0,
) -> dict[str, SemanticScholarSignal]:
    """Fetch Semantic Scholar signals keyed by local paper id."""
    if not papers:
        return {}

    headers = {"x-api-key": api_key} if api_key else {}
    signals: dict[str, SemanticScholarSignal] = {}

    for batch in _chunks(papers, 500):
        ids = [f"ARXIV:{paper.external_ids.arxiv or paper.id}" for paper in batch]
        try:
            async with session.post(
                BASE_URL,
                params={"fields": FIELDS},
                json={"ids": ids},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status >= 400:
                    logger.warning(
                        "Semantic Scholar 请求失败: status=%s", response.status
                    )
                    continue
                payload = await response.json(content_type=None)
        except Exception as exc:
            logger.warning("Semantic Scholar 请求异常: %s", exc)
            continue

        if not isinstance(payload, list):
            continue

        for paper, raw in zip(batch, payload):
            if not isinstance(raw, dict) or not raw.get("paperId"):
                continue
            signals[paper.id] = SemanticScholarSignal(
                paper_id=str(raw["paperId"]),
                citation_count=int(raw.get("citationCount") or 0),
                influential_citation_count=int(
                    raw.get("influentialCitationCount") or 0
                ),
                reference_count=int(raw.get("referenceCount") or 0),
                venue=raw.get("venue") or None,
                publication_types=[
                    str(item) for item in (raw.get("publicationTypes") or [])
                ],
                fields_of_study=_extract_fields_of_study(raw),
                tldr=_extract_tldr(raw),
            )

    return signals
