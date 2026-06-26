"""Tests for daily report models."""

from datetime import datetime, timezone

from src.models import DailyReport, DailyStats


class TestDailyStats:
    def test_valid_stats(self, sample_daily_stats_dict):
        stats = DailyStats(**sample_daily_stats_dict)

        assert stats.total_papers == 50
        assert stats.total_news == 10
        assert "cs.AI" in stats.papers_by_category
        assert "LLM" in stats.top_keywords

    def test_default_values(self):
        stats = DailyStats(total_papers=10, total_news=5)

        assert stats.papers_by_category == {}
        assert stats.news_by_category == {}
        assert stats.top_keywords == []

    def test_empty_stats(self):
        stats = DailyStats(total_papers=0, total_news=0)

        assert stats.total_papers == 0
        assert stats.total_news == 0


class TestDailyReport:
    def test_valid_report(self, sample_daily_stats):
        report = DailyReport(
            date="2025-01-15",
            summary="Collected 50 papers and 10 news items today.",
            category_summaries={"cs.AI": "AI research progress"},
            news_summary="Industry news summary",
            stats=sample_daily_stats,
            generated_at=datetime.now(timezone.utc),
        )

        assert report.date == "2025-01-15"
        assert "50 papers" in report.summary
        assert "cs.AI" in report.category_summaries

    def test_paper_count_property(self, sample_daily_stats):
        report = DailyReport(
            date="2025-01-15",
            summary="Test",
            stats=sample_daily_stats,
            generated_at=datetime.now(timezone.utc),
        )

        assert report.paper_count == 50

    def test_news_count_property(self, sample_daily_stats):
        report = DailyReport(
            date="2025-01-15",
            summary="Test",
            stats=sample_daily_stats,
            generated_at=datetime.now(timezone.utc),
        )

        assert report.news_count == 10

    def test_serialization(self, sample_daily_stats):
        report = DailyReport(
            date="2025-01-15",
            summary="Collected 50 papers and 10 news items today.",
            category_summaries={"cs.AI": "AI research progress"},
            news_summary="Industry news summary",
            stats=sample_daily_stats,
            generated_at=datetime.now(timezone.utc),
        )

        json_str = report.model_dump_json()
        restored = DailyReport.model_validate_json(json_str)

        assert restored.date == report.date
        assert restored.paper_count == report.paper_count
        assert restored.news_count == report.news_count
        assert restored.category_summaries == report.category_summaries
