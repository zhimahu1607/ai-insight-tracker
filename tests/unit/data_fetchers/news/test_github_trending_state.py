"""Tests for GitHub Trending persistent state."""

from datetime import datetime, timedelta, timezone

from src.data_fetchers.news.github_trending_state import (
    DOUBLE_IN_7_DAYS,
    TEN_X_STARS,
    GitHubTrendingState,
)


def test_first_observation_is_new_and_persisted(tmp_path):
    state_path = tmp_path / "github_trending_repos.json"
    state = GitHubTrendingState(state_path)
    observed_at = datetime(2026, 6, 1, tzinfo=timezone.utc)

    decision = state.process_observation(
        repo_id="owner/repo",
        full_name="owner/repo",
        url="https://github.com/owner/repo",
        stars=1200,
        observed_at=observed_at,
    )
    state.save()

    assert decision.is_new is True
    assert decision.alerts == []
    assert state_path.exists()

    reloaded = GitHubTrendingState(state_path)
    assert reloaded.has_repo("owner/repo") is True


def test_seen_repo_is_not_new(tmp_path):
    state = GitHubTrendingState(tmp_path / "state.json")
    observed_at = datetime(2026, 6, 1, tzinfo=timezone.utc)

    state.process_observation(
        repo_id="owner/repo",
        full_name="owner/repo",
        url="https://github.com/owner/repo",
        stars=1200,
        observed_at=observed_at,
    )
    decision = state.process_observation(
        repo_id="owner/repo",
        full_name="owner/repo",
        url="https://github.com/owner/repo",
        stars=1300,
        observed_at=observed_at + timedelta(days=1),
    )

    assert decision.is_new is False
    assert decision.alerts == []


def test_double_within_7_days_alerts_once(tmp_path):
    state = GitHubTrendingState(tmp_path / "state.json")
    observed_at = datetime(2026, 6, 1, tzinfo=timezone.utc)

    state.process_observation(
        repo_id="owner/repo",
        full_name="owner/repo",
        url="https://github.com/owner/repo",
        stars=1200,
        observed_at=observed_at,
    )
    decision = state.process_observation(
        repo_id="owner/repo",
        full_name="owner/repo",
        url="https://github.com/owner/repo",
        stars=2400,
        observed_at=observed_at + timedelta(days=6),
    )
    repeated = state.process_observation(
        repo_id="owner/repo",
        full_name="owner/repo",
        url="https://github.com/owner/repo",
        stars=2500,
        observed_at=observed_at + timedelta(days=6, hours=1),
    )

    assert decision.alerts == [DOUBLE_IN_7_DAYS]
    assert repeated.alerts == []


def test_double_after_7_days_does_not_alert(tmp_path):
    state = GitHubTrendingState(tmp_path / "state.json")
    observed_at = datetime(2026, 6, 1, tzinfo=timezone.utc)

    state.process_observation(
        repo_id="owner/repo",
        full_name="owner/repo",
        url="https://github.com/owner/repo",
        stars=1200,
        observed_at=observed_at,
    )
    decision = state.process_observation(
        repo_id="owner/repo",
        full_name="owner/repo",
        url="https://github.com/owner/repo",
        stars=2400,
        observed_at=observed_at + timedelta(days=8),
    )

    assert decision.alerts == []


def test_ten_x_alerts_once(tmp_path):
    state = GitHubTrendingState(tmp_path / "state.json")
    observed_at = datetime(2026, 6, 1, tzinfo=timezone.utc)

    state.process_observation(
        repo_id="owner/repo",
        full_name="owner/repo",
        url="https://github.com/owner/repo",
        stars=1200,
        observed_at=observed_at,
    )
    decision = state.process_observation(
        repo_id="owner/repo",
        full_name="owner/repo",
        url="https://github.com/owner/repo",
        stars=12000,
        observed_at=observed_at + timedelta(days=30),
    )
    repeated = state.process_observation(
        repo_id="owner/repo",
        full_name="owner/repo",
        url="https://github.com/owner/repo",
        stars=13000,
        observed_at=observed_at + timedelta(days=31),
    )

    assert decision.alerts == [TEN_X_STARS]
    assert repeated.alerts == []
