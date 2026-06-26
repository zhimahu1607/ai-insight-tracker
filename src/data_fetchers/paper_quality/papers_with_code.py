"""Papers with Code quality signals."""

import asyncio
import logging
from typing import Any

import aiohttp

from src.models import CodeRepositorySignal, Paper, PapersWithCodeSignal


logger = logging.getLogger(__name__)

BASE_URL = "https://paperswithcode.com/api/v1"


def _to_repository(raw: dict[str, Any]) -> CodeRepositorySignal:
    return CodeRepositorySignal(
        url=str(raw.get("url") or ""),
        owner=raw.get("owner") or None,
        name=raw.get("name") or None,
        stars=int(raw.get("stars") or 0),
        framework=raw.get("framework") or None,
        is_official=raw.get("is_official"),
    )


async def _fetch_json(
    session: aiohttp.ClientSession,
    url: str,
    *,
    params: dict[str, str] | None = None,
    timeout: float,
) -> dict[str, Any] | None:
    try:
        async with session.get(
            url,
            params=params,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            if response.status == 404:
                return None
            if response.status >= 400:
                logger.warning(
                    "Papers with Code 请求失败: status=%s url=%s",
                    response.status,
                    url,
                )
                return None
            payload = await response.json(content_type=None)
            return payload if isinstance(payload, dict) else None
    except Exception as exc:
        logger.warning("Papers with Code 请求异常: %s", exc)
        return None


async def _fetch_one(
    session: aiohttp.ClientSession,
    paper: Paper,
    *,
    timeout: float,
) -> tuple[str, PapersWithCodeSignal | None]:
    arxiv_id = paper.external_ids.arxiv or paper.id
    paper_payload = await _fetch_json(
        session,
        f"{BASE_URL}/papers/",
        params={"arxiv_id": arxiv_id},
        timeout=timeout,
    )
    results = (paper_payload or {}).get("results") or []
    if not results:
        return paper.id, None

    first = results[0]
    paper_id = str(first.get("id") or "")
    if not paper_id:
        return paper.id, None

    repo_payload = await _fetch_json(
        session,
        f"{BASE_URL}/papers/{paper_id}/repositories/",
        timeout=timeout,
    )
    repositories = [
        _to_repository(item)
        for item in ((repo_payload or {}).get("results") or [])
        if isinstance(item, dict) and item.get("url")
    ]

    return paper.id, PapersWithCodeSignal(
        paper_id=paper_id,
        has_code=bool(repositories),
        repositories=repositories,
    )


async def fetch_papers_with_code_signals(
    session: aiohttp.ClientSession,
    papers: list[Paper],
    *,
    timeout: float = 20.0,
    max_concurrent: int = 5,
) -> dict[str, PapersWithCodeSignal]:
    """Fetch Papers with Code signals keyed by local paper id."""
    if not papers:
        return {}

    semaphore = asyncio.Semaphore(max_concurrent)

    async def guarded(paper: Paper) -> tuple[str, PapersWithCodeSignal | None]:
        async with semaphore:
            return await _fetch_one(session, paper, timeout=timeout)

    pairs = await asyncio.gather(*(guarded(paper) for paper in papers))
    return {paper_id: signal for paper_id, signal in pairs if signal is not None}
