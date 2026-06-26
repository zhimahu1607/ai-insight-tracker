"""Orchestrate external paper quality signal enrichment."""

import asyncio
import logging
from datetime import datetime, timezone

import aiohttp

from src.config.models import PaperQualityConfig
from src.models import Paper, PaperQualitySignals

from .openalex import fetch_openalex_signals
from .papers_with_code import fetch_papers_with_code_signals
from .scorer import score_paper_quality
from .semantic_scholar import fetch_semantic_scholar_signals


logger = logging.getLogger(__name__)


async def enrich_papers_with_quality(
    papers: list[Paper],
    config: PaperQualityConfig,
) -> list[Paper]:
    """Enrich papers with external quality signals and derived scores."""
    if not papers or not config.enabled:
        return papers

    logger.info("开始获取论文外部质量信号: %s 篇", len(papers))
    arxiv_papers = [paper for paper in papers if paper.source == "arxiv"]

    async with aiohttp.ClientSession() as session:
        semantic_task = fetch_semantic_scholar_signals(
            session,
            arxiv_papers,
            api_key=config.semantic_scholar_api_key,
            timeout=config.timeout,
        )
        pwc_task = fetch_papers_with_code_signals(
            session,
            arxiv_papers,
            timeout=config.timeout,
            max_concurrent=config.max_concurrent,
        )
        openalex_task = fetch_openalex_signals(
            session,
            papers,
            email=config.openalex_email,
            timeout=config.timeout,
            max_concurrent=config.max_concurrent,
        )

        semantic, pwc, openalex = await asyncio.gather(
            semantic_task,
            pwc_task,
            openalex_task,
        )

    enriched: list[Paper] = []
    fetched_at = datetime.now(timezone.utc)
    for paper in papers:
        sources: list[str] = []
        semantic_signal = semantic.get(paper.id)
        pwc_signal = pwc.get(paper.id)
        openalex_signal = openalex.get(paper.id)

        if semantic_signal:
            sources.append("semantic_scholar")
        if pwc_signal:
            sources.append("papers_with_code")
        if openalex_signal:
            sources.append("openalex")

        external_ids = paper.external_ids.model_copy(
            update={
                "arxiv": paper.external_ids.arxiv or paper.id,
                "semantic_scholar": (
                    semantic_signal.paper_id
                    if semantic_signal
                    else paper.external_ids.semantic_scholar
                ),
                "openalex": (
                    openalex_signal.work_id
                    if openalex_signal
                    else paper.external_ids.openalex
                ),
            }
        )
        quality_signals = PaperQualitySignals(
            sources=sources,
            fetched_at=fetched_at,
            semantic_scholar=semantic_signal,
            papers_with_code=pwc_signal,
            openalex=openalex_signal,
            openreview=paper.quality_signals.openreview if paper.quality_signals else None,
        )

        enriched_paper = paper.model_copy(
            update={
                "external_ids": external_ids,
                "quality_signals": quality_signals,
            }
        )
        enriched.append(score_paper_quality(enriched_paper))

    scored_count = len([p for p in enriched if p.tracking_score is not None])
    logger.info(
        "论文外部质量信号完成: 有评分 %s/%s 篇",
        scored_count,
        len(enriched),
    )
    return enriched
