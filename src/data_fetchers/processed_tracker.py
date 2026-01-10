"""
兼容层：ProcessedTracker（历史名称）

该项目已将 “抓取去重(fetched)” 与 “分析去重(analyzed)” 拆分为两套 ID 文件：
- data/fetched_ids.json
- data/analyzed_ids.json

历史代码中使用的 ProcessedTracker / get_processed_tracker 仍然保留，但语义上等价于
“抓取去重追踪器（fetched）”。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .ids_tracker import IdsTracker, IdsTrackerPaths, get_analyzed_tracker, get_fetched_tracker

_tracker: Optional["ProcessedTracker"] = None


class ProcessedTracker(IdsTracker):
    """兼容旧类名：等价于 IdsTracker（默认指向 fetched_ids.json）。"""

    DEFAULT_FILE = IdsTrackerPaths.fetched
    RETENTION_DAYS = IdsTracker.RETENTION_DAYS

    def __init__(self, file_path: Optional[str | Path] = None, retention_days: int = RETENTION_DAYS):
        super().__init__(file_path=file_path or self.DEFAULT_FILE, retention_days=retention_days)

    # 兼容旧方法名
    def get_processed_paper_ids(self) -> set[str]:
        return self.get_paper_ids()

    def get_processed_news_ids(self) -> set[str]:
        return self.get_news_ids()

    def mark_papers_processed(self, paper_ids: list[str]) -> None:
        self.mark_papers(paper_ids)

    def mark_news_processed(self, news_ids: list[str]) -> None:
        self.mark_news(news_ids)


def get_processed_tracker(file_path: Optional[str | Path] = None) -> ProcessedTracker:
    """
    兼容旧入口：默认返回 fetched tracker（历史去重/抓取去重）。

    注意：保持旧行为——全局单例。第一次调用决定 file_path，之后调用将复用同一实例。
    """
    global _tracker
    if _tracker is None:
        # 优先使用传入路径，否则指向 fetched_ids.json
        _tracker = ProcessedTracker(file_path=file_path or IdsTrackerPaths.fetched)
    return _tracker


def reset_processed_tracker() -> None:
    global _tracker
    _tracker = None

    # 同时重置新追踪器单例，避免测试/脚本复用进程时污染
    from .ids_tracker import reset_ids_trackers

    reset_ids_trackers()


__all__ = [
    "IdsTracker",
    "IdsTrackerPaths",
    "ProcessedTracker",
    "get_fetched_tracker",
    "get_analyzed_tracker",
    "get_processed_tracker",
    "reset_processed_tracker",
]

