"""OpenAlex quality signals."""

import asyncio
import logging
import re
from typing import Any

import aiohttp

from src.models import OpenAlexSignal, Paper


logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org/works"


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _title_matches(local_title: str, remote_title: str) -> bool:
    local = _normalize_title(local_title)
    remote = _normalize_title(remote_title)
    if not local or not remote:
        return False
    return local == remote or local in remote or remote in local


def _extract_institutions(raw: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    for authorship in raw.get("authorships") or []:
        if not isinstance(authorship, dict):
            continue
        for institution in authorship.get("institutions") or []:
            if isinstance(institution, dict) and institution.get("display_name"):
                names.add(str(institution["display_name"]))
    return sorted(names)


def _extract_topics(raw: dict[str, Any]) -> list[str]:
    topics: set[str] = set()
    primary_topic = raw.get("primary_topic")
    if isinstance(primary_topic, dict) and primary_topic.get("display_name"):
        topics.add(str(primary_topic["display_name"]))
    for topic in raw.get("topics") or []:
        if isinstance(topic, dict) and topic.get("display_name"):
            topics.add(str(topic["display_name"]))
    return sorted(topics)


def _extract_source(raw: dict[str, Any]) -> str | None:
    primary_location = raw.get("primary_location")
    if not isinstance(primary_location, dict):
        return None
    source = primary_location.get("source")
    if isinstance(source, dict) and source.get("display_name"):
        return str(source["display_name"])
    return None


async def _fetch_one(
    session: aiohttp.ClientSession,
    paper: Paper,
    *,
    email: str,
    timeout: float,
) -> tuple[str, OpenAlexSignal | None]:
    params = {
        "search": paper.title,
        "per_page": "1",
        "select": (
            "id,display_name,cited_by_count,fwci,authorships,"
            "primary_topic,topics,primary_location"
        ),
    }
    if email:
        params["mailto"] = email

    try:
        async with session.get(
            BASE_URL,
            params=params,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            if response.status >= 400:
                logger.warning("OpenAlex 请求失败: status=%s", response.status)
                return paper.id, None
            payload = await response.json(content_type=None)
    except Exception as exc:
        logger.warning("OpenAlex 请求异常: %s", exc)
        return paper.id, None

    results = payload.get("results") if isinstance(payload, dict) else None
    if not results or not isinstance(results[0], dict):
        return paper.id, None

    raw = results[0]
    if not _title_matches(paper.title, str(raw.get("display_name") or "")):
        return paper.id, None

    return paper.id, OpenAlexSignal(
        work_id=str(raw.get("id") or ""),
        cited_by_count=int(raw.get("cited_by_count") or 0),
        fwci=raw.get("fwci"),
        institutions=_extract_institutions(raw),
        topics=_extract_topics(raw),
        source=_extract_source(raw),
    )


async def fetch_openalex_signals(
    session: aiohttp.ClientSession,
    papers: list[Paper],
    *,
    email: str = "",
    timeout: float = 20.0,
    max_concurrent: int = 5,
) -> dict[str, OpenAlexSignal]:
    """Fetch OpenAlex signals keyed by local paper id."""
    if not papers:
        return {}

    semaphore = asyncio.Semaphore(max_concurrent)

    async def guarded(paper: Paper) -> tuple[str, OpenAlexSignal | None]:
        async with semaphore:
            return await _fetch_one(session, paper, email=email, timeout=timeout)

    pairs = await asyncio.gather(*(guarded(paper) for paper in papers))
    return {paper_id: signal for paper_id, signal in pairs if signal is not None}
