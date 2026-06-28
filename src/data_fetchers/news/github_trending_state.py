"""Persistent state for GitHub Trending repositories."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


DOUBLE_IN_7_DAYS = "double_in_7_days"
TEN_X_STARS = "ten_x_stars"


@dataclass
class GitHubTrendingRecord:
    repo_id: str
    full_name: str
    url: str
    first_seen_at: str
    first_seen_stars: int
    last_seen_at: str
    last_seen_stars: int
    double_alerted_at: Optional[str] = None
    ten_x_alerted_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "GitHubTrendingRecord":
        return cls(
            repo_id=str(data["repo_id"]),
            full_name=str(data["full_name"]),
            url=str(data["url"]),
            first_seen_at=str(data["first_seen_at"]),
            first_seen_stars=int(data["first_seen_stars"]),
            last_seen_at=str(data["last_seen_at"]),
            last_seen_stars=int(data["last_seen_stars"]),
            double_alerted_at=(
                str(data["double_alerted_at"]) if data.get("double_alerted_at") else None
            ),
            ten_x_alerted_at=(
                str(data["ten_x_alerted_at"]) if data.get("ten_x_alerted_at") else None
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "repo_id": self.repo_id,
            "full_name": self.full_name,
            "url": self.url,
            "first_seen_at": self.first_seen_at,
            "first_seen_stars": self.first_seen_stars,
            "last_seen_at": self.last_seen_at,
            "last_seen_stars": self.last_seen_stars,
            "double_alerted_at": self.double_alerted_at,
            "ten_x_alerted_at": self.ten_x_alerted_at,
        }


@dataclass(frozen=True)
class GitHubTrendingDecision:
    is_new: bool
    alerts: list[str]


class GitHubTrendingState:
    """Track seen repositories and star-growth alerts."""

    def __init__(self, file_path: str | Path = "data/github_trending_repos.json") -> None:
        self._file_path = Path(file_path)
        self._records: dict[str, GitHubTrendingRecord] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        if not self._file_path.exists():
            self._loaded = True
            return

        try:
            data = json.loads(self._file_path.read_text(encoding="utf-8"))
            records = data.get("repositories", {}) if isinstance(data, dict) else {}
            if isinstance(records, dict):
                self._records = {
                    repo_id: GitHubTrendingRecord.from_dict(record)
                    for repo_id, record in records.items()
                    if isinstance(record, dict)
                }
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning("Failed to load GitHub Trending state: %s", e)
            self._records = {}

        self._loaded = True

    def save(self) -> None:
        self.load()
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "repositories": {
                repo_id: record.to_dict()
                for repo_id, record in sorted(self._records.items())
            }
        }
        self._file_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def has_repo(self, repo_id: str) -> bool:
        self.load()
        return repo_id in self._records

    def process_observation(
        self,
        *,
        repo_id: str,
        full_name: str,
        url: str,
        stars: int,
        observed_at: datetime,
    ) -> GitHubTrendingDecision:
        """Update state for a repository and return whether to emit items."""
        self.load()
        now = _ensure_utc(observed_at)
        now_iso = now.isoformat()
        record = self._records.get(repo_id)

        if record is None:
            self._records[repo_id] = GitHubTrendingRecord(
                repo_id=repo_id,
                full_name=full_name,
                url=url,
                first_seen_at=now_iso,
                first_seen_stars=stars,
                last_seen_at=now_iso,
                last_seen_stars=stars,
            )
            return GitHubTrendingDecision(is_new=True, alerts=[])

        alerts: list[str] = []
        first_seen_at = _parse_iso(record.first_seen_at)

        if (
            record.double_alerted_at is None
            and now - first_seen_at <= timedelta(days=7)
            and stars >= record.first_seen_stars * 2
        ):
            alerts.append(DOUBLE_IN_7_DAYS)
            record.double_alerted_at = now_iso

        if record.ten_x_alerted_at is None and stars >= record.first_seen_stars * 10:
            alerts.append(TEN_X_STARS)
            record.ten_x_alerted_at = now_iso

        record.full_name = full_name
        record.url = url
        record.last_seen_at = now_iso
        record.last_seen_stars = stars

        return GitHubTrendingDecision(is_new=False, alerts=alerts)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return _ensure_utc(parsed)
