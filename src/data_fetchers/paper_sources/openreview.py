"""OpenReview accepted paper source."""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

import aiohttp

from src.models import (
    OpenReviewSignal,
    Paper,
    PaperExternalIds,
    PaperQualitySignals,
)
from src.data_fetchers.paper_quality.scorer import score_paper_quality


logger = logging.getLogger(__name__)

BASE_URL = "https://api2.openreview.net/notes"
FORUM_URL = "https://openreview.net/forum?id={id}"
PDF_URL = "https://openreview.net/pdf?id={id}"


def _content_value(content: dict[str, Any], key: str, default: Any = None) -> Any:
    value = content.get(key, default)
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def _timestamp_to_datetime(value: Any) -> datetime:
    try:
        timestamp = int(value) / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _extract_decision(replies: list[dict[str, Any]]) -> str | None:
    for reply in replies:
        invitations = reply.get("invitations") or []
        if any(str(item).endswith("Decision") for item in invitations):
            content = reply.get("content") or {}
            decision = _content_value(content, "decision")
            if decision:
                return str(decision)
    return None


def _extract_reviews(replies: list[dict[str, Any]]) -> tuple[float | None, float | None, int]:
    ratings: list[float] = []
    confidences: list[float] = []
    for reply in replies:
        invitations = reply.get("invitations") or []
        if not any(str(item).endswith("Official_Review") for item in invitations):
            continue
        content = reply.get("content") or {}
        rating = _content_value(content, "rating")
        confidence = _content_value(content, "confidence")
        rating_number = _extract_number(rating)
        confidence_number = _extract_number(confidence)
        if rating_number is not None:
            ratings.append(rating_number)
        if confidence_number is not None:
            confidences.append(confidence_number)

    rating_avg = sum(ratings) / len(ratings) if ratings else None
    confidence_avg = sum(confidences) / len(confidences) if confidences else None
    return rating_avg, confidence_avg, len(ratings)


def _extract_number(value: Any) -> float | None:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group()) if match else None


def _is_accepted(decision: str | None) -> bool:
    if not decision:
        return False
    lowered = decision.lower()
    reject_terms = {"reject", "withdraw", "desk reject"}
    if any(term in lowered for term in reject_terms):
        return False
    return any(term in lowered for term in ["accept", "spotlight", "oral", "poster"])


def _to_paper(note: dict[str, Any], venue_id: str, primary_category: str) -> Paper | None:
    content = note.get("content") or {}
    replies = ((note.get("details") or {}).get("replies") or [])
    decision = _extract_decision(replies)
    if not _is_accepted(decision):
        return None

    note_id = str(note.get("forum") or note.get("id") or "")
    if not note_id:
        return None

    title = str(_content_value(content, "title", "") or "").strip()
    abstract = str(_content_value(content, "abstract", "") or "").strip()
    authors = _content_value(content, "authors", []) or []
    if not title or not abstract:
        return None

    if not isinstance(authors, list):
        authors = [str(authors)]

    rating_avg, confidence_avg, review_count = _extract_reviews(replies)
    signal = OpenReviewSignal(
        forum_id=note_id,
        venue_id=venue_id,
        decision=decision,
        rating_avg=rating_avg,
        confidence_avg=confidence_avg,
        review_count=review_count,
    )
    quality_signals = PaperQualitySignals(
        sources=["openreview"],
        fetched_at=datetime.now(timezone.utc),
        openreview=signal,
    )
    paper = Paper(
        id=f"openreview:{note_id}",
        source="openreview",
        external_ids=PaperExternalIds(openreview=note_id),
        title=title,
        authors=[str(author) for author in authors],
        abstract=abstract,
        categories=[primary_category],
        primary_category=primary_category,
        pdf_url=PDF_URL.format(id=note_id),
        abs_url=FORUM_URL.format(id=note_id),
        published=_timestamp_to_datetime(note.get("pdate") or note.get("cdate")),
        updated=_timestamp_to_datetime(note.get("mdate") or note.get("tmdate")),
        comment=f"OpenReview venue: {venue_id}; decision: {decision}",
        quality_signals=quality_signals,
    )
    return score_paper_quality(paper)


async def _fetch_venue(
    session: aiohttp.ClientSession,
    venue_id: str,
    *,
    primary_category: str,
    timeout: float,
) -> list[Paper]:
    params = {
        "invitation": f"{venue_id}/-/Submission",
        "details": "replies",
        "limit": "1000",
    }
    try:
        async with session.get(
            BASE_URL,
            params=params,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            if response.status >= 400:
                logger.warning("OpenReview 请求失败: %s status=%s", venue_id, response.status)
                return []
            payload = await response.json(content_type=None)
    except Exception as exc:
        logger.warning("OpenReview 请求异常: %s venue=%s", exc, venue_id)
        return []

    notes = payload.get("notes") if isinstance(payload, dict) else []
    papers: list[Paper] = []
    for note in notes or []:
        if not isinstance(note, dict):
            continue
        paper = _to_paper(note, venue_id, primary_category)
        if paper:
            papers.append(paper)
    return papers


async def fetch_openreview_papers(
    venues: list[str],
    *,
    primary_category: str = "cs.AI",
    timeout: float = 20.0,
) -> list[Paper]:
    """Fetch accepted papers from configured OpenReview venues."""
    if not venues:
        return []

    logger.info("开始获取 OpenReview 高质量来源: %s", venues)
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *(
                _fetch_venue(
                    session,
                    venue,
                    primary_category=primary_category,
                    timeout=timeout,
                )
                for venue in venues
            )
        )

    papers = [paper for group in results for paper in group]
    logger.info("OpenReview 获取完成: %s 篇 accepted 论文", len(papers))
    return papers
