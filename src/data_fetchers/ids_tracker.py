"""
ID 追踪器（fetched / analyzed）

用于管理 papers/news 两类内容的 ID 集合，支持：
- 加载/保存 JSON 文件
- 标记已记录 ID（写入时间戳）
- 获取已记录集合
- 自动清理超过 retention_days 的记录
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IdsTrackerPaths:
    fetched: str = "data/fetched_ids.json"
    analyzed: str = "data/analyzed_ids.json"


class IdsTracker:
    """
    通用 ID 追踪器

    文件结构：
    {
      "papers": { "<id>": "<iso timestamp>", ... },
      "news": { "<id>": "<iso timestamp>", ... }
    }
    """

    RETENTION_DAYS = 30

    def __init__(
        self,
        file_path: Optional[str | Path] = None,
        retention_days: int = RETENTION_DAYS,
    ):
        self._file_path = Path(file_path) if file_path else Path(IdsTrackerPaths.fetched)
        self._retention_days = retention_days
        self._data: dict[str, dict[str, str]] = {"papers": {}, "news": {}}
        self._loaded = False

    @property
    def file_path(self) -> Path:
        return self._file_path

    def load(self) -> None:
        if self._loaded:
            return

        if not self._file_path.exists():
            logger.info(f"ID 文件不存在，将创建新文件: {self._file_path}")
            self._loaded = True
            return

        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                self._data["papers"] = data.get("papers", {}) or {}
                self._data["news"] = data.get("news", {}) or {}

            logger.info(
                f"ID 文件加载完成: {len(self._data['papers'])} papers, {len(self._data['news'])} news"
            )
            self._loaded = True
        except json.JSONDecodeError as e:
            logger.warning(f"解析 ID 文件失败: {e}，将使用空记录")
            self._loaded = True
        except OSError as e:
            logger.warning(f"读取 ID 文件失败: {e}，将使用空记录")
            self._loaded = True

    def save(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def cleanup(self) -> int:
        self.load()

        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        cutoff_str = cutoff.isoformat()

        cleaned_count = 0
        for category in ("papers", "news"):
            original_count = len(self._data[category])
            self._data[category] = {
                id_: ts for id_, ts in self._data[category].items() if ts >= cutoff_str
            }
            cleaned_count += original_count - len(self._data[category])

        if cleaned_count > 0:
            logger.info(f"清理过期 ID 记录: {cleaned_count} 条 ({self._file_path})")
            self.save()

        return cleaned_count

    def get_paper_ids(self) -> set[str]:
        self.load()
        return set(self._data["papers"].keys())

    def get_news_ids(self) -> set[str]:
        self.load()
        return set(self._data["news"].keys())

    def mark_papers(self, paper_ids: list[str]) -> None:
        self.load()
        now = datetime.now(timezone.utc).isoformat()
        for pid in paper_ids:
            if pid not in self._data["papers"]:
                self._data["papers"][pid] = now
        self.save()

    def mark_news(self, news_ids: list[str]) -> None:
        self.load()
        now = datetime.now(timezone.utc).isoformat()
        for nid in news_ids:
            if nid not in self._data["news"]:
                self._data["news"][nid] = now
        self.save()


_fetched_tracker: Optional[IdsTracker] = None
_analyzed_tracker: Optional[IdsTracker] = None


def get_fetched_tracker(file_path: Optional[str | Path] = None) -> IdsTracker:
    global _fetched_tracker
    if _fetched_tracker is None:
        _fetched_tracker = IdsTracker(
            file_path=file_path or IdsTrackerPaths.fetched,
            retention_days=IdsTracker.RETENTION_DAYS,
        )
    return _fetched_tracker


def get_analyzed_tracker(file_path: Optional[str | Path] = None) -> IdsTracker:
    global _analyzed_tracker
    if _analyzed_tracker is None:
        _analyzed_tracker = IdsTracker(
            file_path=file_path or IdsTrackerPaths.analyzed,
            retention_days=IdsTracker.RETENTION_DAYS,
        )
    return _analyzed_tracker


def reset_ids_trackers() -> None:
    global _fetched_tracker, _analyzed_tracker
    _fetched_tracker = None
    _analyzed_tracker = None


