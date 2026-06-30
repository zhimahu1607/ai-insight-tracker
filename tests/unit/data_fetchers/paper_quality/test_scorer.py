"""Paper quality scorer tests."""

from datetime import datetime, timezone

from src.data_fetchers.paper_quality.scorer import filter_tracked_papers


def _paper_with_score(sample_paper, paper_id: str, score: float | None, day: int = 1):
    return sample_paper.model_copy(
        update={
            "id": paper_id,
            "quality_score": score,
            "tracking_score": score,
            "published": datetime(2026, 1, day, tzinfo=timezone.utc),
        }
    )


def test_filter_tracked_papers_keeps_only_min_score_or_above(sample_paper):
    high = _paper_with_score(sample_paper, "high", 75.0)
    low = _paper_with_score(sample_paper, "low", 69.9)
    unscored = _paper_with_score(sample_paper, "unscored", None)

    kept, rejected = filter_tracked_papers(
        [low, unscored, high],
        min_score=70.0,
        max_per_category=10,
        max_total=30,
    )

    assert [paper.id for paper in kept] == ["high"]
    assert {paper.id for paper in rejected} == {"low", "unscored"}


def test_filter_tracked_papers_applies_total_limit_by_score(sample_paper):
    top = _paper_with_score(sample_paper, "top", 95.0, day=1)
    middle = _paper_with_score(sample_paper, "middle", 85.0, day=2)
    bottom = _paper_with_score(sample_paper, "bottom", 75.0, day=3)

    kept, rejected = filter_tracked_papers(
        [bottom, middle, top],
        min_score=70.0,
        max_per_category=10,
        max_total=2,
    )

    assert [paper.id for paper in kept] == ["top", "middle"]
    assert [paper.id for paper in rejected] == ["bottom"]


def test_filter_tracked_papers_applies_category_limit(sample_paper):
    first = _paper_with_score(sample_paper, "first", 90.0, day=1)
    second = _paper_with_score(sample_paper, "second", 80.0, day=2)
    other_category = _paper_with_score(sample_paper, "other", 75.0, day=3).model_copy(
        update={"primary_category": "cs.CL", "categories": ["cs.CL"]}
    )

    kept, rejected = filter_tracked_papers(
        [second, other_category, first],
        min_score=70.0,
        max_per_category=1,
        max_total=30,
    )

    assert [paper.id for paper in kept] == ["first", "other"]
    assert [paper.id for paper in rejected] == ["second"]
