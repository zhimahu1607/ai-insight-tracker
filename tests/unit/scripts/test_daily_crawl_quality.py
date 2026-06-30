"""Daily crawl quality gate tests."""

from datetime import datetime, timezone
from unittest.mock import patch

from scripts.daily_crawl import get_today_date, should_analyze_paper
from src.config.models import PaperQualityConfig, Settings
from src.models import AnalyzedPaper


def _settings(*, enabled: bool = True, min_score: float = 70.0) -> Settings:
    return Settings(
        paper_quality=PaperQualityConfig(
            enabled=enabled,
            min_tracking_score=min_score,
        )
    )


def _analyzed_paper(sample_paper, score: float | None) -> AnalyzedPaper:
    paper = sample_paper.model_copy(
        update={
            "quality_score": score,
            "tracking_score": score,
        }
    )
    return AnalyzedPaper(**paper.model_dump(), analysis_status="pending")


def test_get_today_date_uses_beijing_timezone_for_utc_schedule_boundary():
    assert get_today_date(datetime(2026, 6, 30, 15, 59, tzinfo=timezone.utc)) == "2026-06-30"
    assert get_today_date(datetime(2026, 6, 30, 16, 0, tzinfo=timezone.utc)) == "2026-07-01"


def test_should_analyze_paper_requires_min_tracking_score(sample_paper):
    high = _analyzed_paper(sample_paper, 70.0)
    low = _analyzed_paper(sample_paper, 69.9)
    unscored = _analyzed_paper(sample_paper, None)

    with patch("scripts.daily_crawl.get_settings", return_value=_settings()):
        assert should_analyze_paper(high) is True
        assert should_analyze_paper(low) is False
        assert should_analyze_paper(unscored) is False


def test_should_analyze_paper_does_not_bypass_when_quality_disabled(sample_paper):
    high = _analyzed_paper(sample_paper, 95.0)

    with patch("scripts.daily_crawl.get_settings", return_value=_settings(enabled=False)):
        assert should_analyze_paper(high) is False
