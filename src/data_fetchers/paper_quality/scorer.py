"""Paper quality scoring and filtering."""

import math
from collections import defaultdict
from datetime import datetime, timezone

from src.models import Paper, PaperQualitySignals


TOP_VENUE_KEYWORDS = {
    "neurips",
    "iclr",
    "icml",
    "acl",
    "emnlp",
    "naacl",
    "cvpr",
    "iccv",
    "eccv",
    "colm",
    "aaai",
    "ijcai",
    "siggraph",
}

TRUSTED_INSTITUTION_KEYWORDS = {
    "anthropic",
    "berkeley",
    "cambridge",
    "carnegie mellon",
    "cmu",
    "deepmind",
    "eth",
    "google",
    "meta",
    "microsoft",
    "mit",
    "openai",
    "oxford",
    "peking university",
    "princeton",
    "stanford",
    "tsinghua",
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _source_count(signals: PaperQualitySignals | None) -> int:
    return len(signals.sources) if signals else 0


def _score_venue_or_review(signals: PaperQualitySignals | None) -> tuple[float, list[str]]:
    if not signals:
        return 0.0, []

    reasons: list[str] = []
    openreview = signals.openreview
    if openreview:
        decision = (openreview.decision or "").lower()
        if "accept" in decision or "spotlight" in decision or "oral" in decision:
            reasons.append(f"OpenReview decision: {openreview.decision}")
            return 100.0, reasons
        if openreview.rating_avg is not None:
            score = _clamp((openreview.rating_avg / 10.0) * 100.0)
            reasons.append(f"OpenReview avg rating {openreview.rating_avg:.1f}")
            return score, reasons

    venues = [
        signals.semantic_scholar.venue if signals.semantic_scholar else None,
        signals.openalex.source if signals.openalex else None,
    ]
    publication_types = (
        signals.semantic_scholar.publication_types
        if signals.semantic_scholar
        else []
    )

    venue_text = " ".join(v for v in venues if v).lower()
    if any(keyword in venue_text for keyword in TOP_VENUE_KEYWORDS):
        reasons.append("top-tier venue signal")
        return 85.0, reasons
    if any("conference" in item.lower() for item in publication_types):
        reasons.append("conference publication signal")
        return 55.0, reasons
    return 0.0, reasons


def _score_code(signals: PaperQualitySignals | None) -> tuple[float, list[str]]:
    pwc = signals.papers_with_code if signals else None
    if not pwc or not pwc.repositories:
        return 0.0, []

    max_stars = max(repo.stars for repo in pwc.repositories)
    has_official = any(repo.is_official for repo in pwc.repositories)
    score = 70.0 + min(20.0, math.log1p(max_stars) * 4.0)
    if has_official:
        score += 10.0

    reasons = ["Papers with Code repository found"]
    if has_official:
        reasons.append("official implementation available")
    if max_stars:
        reasons.append(f"top repo stars: {max_stars}")
    return _clamp(score), reasons


def _paper_age_months(paper: Paper) -> float:
    now = datetime.now(timezone.utc)
    published = paper.published
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    days = max(1, (now - published).days)
    return max(1.0, days / 30.0)


def _score_citations(
    paper: Paper, signals: PaperQualitySignals | None
) -> tuple[float, list[str]]:
    if not signals:
        return 0.0, []

    citation_count = 0
    influential_count = 0
    if signals.semantic_scholar:
        citation_count = max(citation_count, signals.semantic_scholar.citation_count)
        influential_count = max(
            influential_count, signals.semantic_scholar.influential_citation_count
        )
    if signals.openalex:
        citation_count = max(citation_count, signals.openalex.cited_by_count)

    if citation_count <= 0 and influential_count <= 0:
        return 0.0, []

    age_months = _paper_age_months(paper)
    citation_velocity = citation_count / age_months
    influence_velocity = influential_count / age_months
    score = math.log1p(citation_velocity) * 25.0
    score += math.log1p(influence_velocity) * 35.0

    reasons = [f"citations: {citation_count}"]
    if influential_count:
        reasons.append(f"influential citations: {influential_count}")
    return _clamp(score), reasons


def _score_author_institution(signals: PaperQualitySignals | None) -> tuple[float, list[str]]:
    institutions = signals.openalex.institutions if signals and signals.openalex else []
    text = " ".join(institutions).lower()
    hits = [
        keyword
        for keyword in TRUSTED_INSTITUTION_KEYWORDS
        if keyword in text
    ]
    if not hits:
        return 0.0, []
    return 75.0, [f"trusted institution signal: {hits[0]}"]


def _score_metadata_confidence(signals: PaperQualitySignals | None) -> tuple[float, str]:
    count = _source_count(signals)
    if count >= 3:
        return 100.0, "high"
    if count == 2:
        return 70.0, "medium"
    if count == 1:
        return 40.0, "low"
    return 0.0, "low"


def score_paper_quality(paper: Paper) -> Paper:
    """Return a copy of paper with quality score fields updated."""
    signals = paper.quality_signals
    if not signals or not signals.sources:
        return paper.model_copy(
            update={
                "quality_score": None,
                "tracking_score": None,
                "quality_confidence": "low",
                "quality_reasons": ["external quality signals unavailable"],
            }
        )

    venue_score, venue_reasons = _score_venue_or_review(signals)
    code_score, code_reasons = _score_code(signals)
    citation_score, citation_reasons = _score_citations(paper, signals)
    institution_score, institution_reasons = _score_author_institution(signals)
    metadata_score, confidence = _score_metadata_confidence(signals)

    quality_score = (
        0.30 * venue_score
        + 0.20 * code_score
        + 0.20 * citation_score
        + 0.15 * institution_score
        + 0.15 * metadata_score
    )
    if venue_score >= 100:
        quality_score = max(quality_score, 90.0)
    elif venue_score >= 85:
        quality_score = max(quality_score, 75.0)
    if code_score >= 90:
        quality_score = max(quality_score, 72.0)

    reasons = (
        venue_reasons
        + code_reasons
        + citation_reasons
        + institution_reasons
        + [f"quality sources: {', '.join(signals.sources)}"]
    )

    return paper.model_copy(
        update={
            "quality_score": round(_clamp(quality_score), 1),
            "tracking_score": round(_clamp(quality_score), 1),
            "quality_confidence": confidence,
            "quality_reasons": reasons[:4],
        }
    )


def filter_tracked_papers(
    papers: list[Paper],
    *,
    min_score: float,
    candidate_min_score: float,
    max_per_category: int,
    max_total: int,
) -> tuple[list[Paper], list[Paper]]:
    """
    Split papers into kept/rejected candidates.

    Papers with no score are kept as fail-open candidates. Scored papers below the
    candidate threshold are rejected before expensive LLM analysis.
    """
    eligible: list[Paper] = []
    rejected: list[Paper] = []

    for paper in papers:
        score = paper.tracking_score
        if score is None or score >= candidate_min_score:
            eligible.append(paper)
        else:
            rejected.append(paper)

    def sort_key(paper: Paper) -> tuple[float, float]:
        score = paper.tracking_score if paper.tracking_score is not None else -1.0
        return (-score, -paper.published.timestamp())

    eligible = sorted(eligible, key=sort_key)
    if max_total <= 0 and max_per_category <= 0:
        return eligible, rejected

    kept: list[Paper] = []
    counts_by_category: dict[str, int] = defaultdict(int)
    for paper in eligible:
        score = paper.tracking_score
        is_high_score = score is not None and score >= min_score
        is_unknown = score is None
        category_count = counts_by_category[paper.primary_category]

        if max_total > 0 and len([p for p in kept if p.tracking_score is not None]) >= max_total:
            if not is_unknown:
                rejected.append(paper)
                continue
        if (
            max_per_category > 0
            and category_count >= max_per_category
            and is_high_score
        ):
            rejected.append(paper)
            continue

        kept.append(paper)
        if is_high_score:
            counts_by_category[paper.primary_category] += 1

    return kept, rejected
