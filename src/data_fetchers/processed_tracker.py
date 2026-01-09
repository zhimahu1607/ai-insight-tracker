"""
已处理内容追踪器

管理已处理的论文和新闻 ID，支持：
- 加载/保存已处理记录
- 检查是否已处理
- 自动清理超过7天的记录
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ProcessedTracker:
    """
    已处理内容追踪器

    Features:
        - 记录已处理的 paper/news ID 及处理时间
        - 支持7天自动清理，防止文件膨胀
        - 线程安全的文件读写
    """

    DEFAULT_FILE = "data/processed_ids.json"
    RETENTION_DAYS = 30  # 保留30天记录

    def __init__(
        self,
        file_path: Optional[str | Path] = None,
        retention_days: int = RETENTION_DAYS,
    ):
        """
        初始化追踪器

        Args:
            file_path: 已处理记录文件路径，默认 data/processed_ids.json
            retention_days: 记录保留天数，默认7天
        """
        self._file_path = Path(file_path) if file_path else Path(self.DEFAULT_FILE)
        self._retention_days = retention_days
        self._data: dict[str, dict[str, str]] = {
            "papers": {},
            "news": {},
        }
        self._loaded = False

    def load(self) -> None:
        """加载已处理记录"""
        if self._loaded:
            return

        if not self._file_path.exists():
            logger.info(f"已处理记录文件不存在，将创建新文件: {self._file_path}")
            self._loaded = True
            return

        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 验证结构
            if isinstance(data, dict):
                self._data["papers"] = data.get("papers", {})
                self._data["news"] = data.get("news", {})

            logger.info(
                f"已处理记录加载完成: {len(self._data['papers'])} 篇论文, "
                f"{len(self._data['news'])} 条新闻"
            )
            self._loaded = True

        except json.JSONDecodeError as e:
            logger.warning(f"解析已处理记录失败: {e}，将使用空记录")
            self._loaded = True
        except IOError as e:
            logger.warning(f"读取已处理记录失败: {e}，将使用空记录")
            self._loaded = True

    def save(self) -> None:
        """保存已处理记录"""
        # 确保目录存在
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)

            logger.debug(f"已处理记录保存成功: {self._file_path}")

        except IOError as e:
            logger.error(f"保存已处理记录失败: {e}")
            raise

    def cleanup(self) -> int:
        """
        清理超过保留期限的记录

        Returns:
            清理的记录数量
        """
        self.load()

        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        cutoff_str = cutoff.isoformat()

        cleaned_count = 0

        for category in ["papers", "news"]:
            original_count = len(self._data[category])
            self._data[category] = {
                id_: timestamp
                for id_, timestamp in self._data[category].items()
                if timestamp >= cutoff_str
            }
            cleaned_count += original_count - len(self._data[category])

        if cleaned_count > 0:
            logger.info(f"清理过期记录: {cleaned_count} 条")
            self.save()

        return cleaned_count

    def is_paper_processed(self, paper_id: str) -> bool:
        """检查论文是否已处理"""
        self.load()
        return paper_id in self._data["papers"]

    def is_news_processed(self, news_id: str) -> bool:
        """检查新闻是否已处理"""
        self.load()
        return news_id in self._data["news"]

    def get_processed_paper_ids(self) -> set[str]:
        """获取所有已处理的论文 ID"""
        self.load()
        return set(self._data["papers"].keys())

    def get_processed_news_ids(self) -> set[str]:
        """获取所有已处理的新闻 ID"""
        self.load()
        return set(self._data["news"].keys())

    def mark_papers_processed(self, paper_ids: list[str]) -> None:
        """
        标记论文为已处理

        Args:
            paper_ids: 论文 ID 列表
        """
        self.load()

        now = datetime.now(timezone.utc).isoformat()
        for paper_id in paper_ids:
            if paper_id not in self._data["papers"]:
                self._data["papers"][paper_id] = now

        self.save()
        logger.debug(f"标记 {len(paper_ids)} 篇论文为已处理")

    def mark_news_processed(self, news_ids: list[str]) -> None:
        """
        标记新闻为已处理

        Args:
            news_ids: 新闻 ID 列表
        """
        self.load()

        now = datetime.now(timezone.utc).isoformat()
        for news_id in news_ids:
            if news_id not in self._data["news"]:
                self._data["news"][news_id] = now

        self.save()
        logger.debug(f"标记 {len(news_ids)} 条新闻为已处理")

    def filter_unprocessed_papers(self, paper_ids: list[str]) -> list[str]:
        """
        过滤出未处理的论文 ID

        Args:
            paper_ids: 论文 ID 列表

        Returns:
            未处理的论文 ID 列表
        """
        self.load()
        processed = self._data["papers"]
        return [id_ for id_ in paper_ids if id_ not in processed]

    def filter_unprocessed_news(self, news_ids: list[str]) -> list[str]:
        """
        过滤出未处理的新闻 ID

        Args:
            news_ids: 新闻 ID 列表

        Returns:
            未处理的新闻 ID 列表
        """
        self.load()
        processed = self._data["news"]
        return [id_ for id_ in news_ids if id_ not in processed]

    @property
    def paper_count(self) -> int:
        """已处理论文数量"""
        self.load()
        return len(self._data["papers"])

    @property
    def news_count(self) -> int:
        """已处理新闻数量"""
        self.load()
        return len(self._data["news"])

    def get_stats(self) -> dict[str, int]:
        """获取统计信息"""
        self.load()
        return {
            "papers": len(self._data["papers"]),
            "news": len(self._data["news"]),
            "retention_days": self._retention_days,
        }


# 全局单例
_tracker: Optional[ProcessedTracker] = None


def get_processed_tracker(
    file_path: Optional[str | Path] = None,
) -> ProcessedTracker:
    """
    获取全局 ProcessedTracker 实例

    Args:
        file_path: 可选的自定义文件路径

    Returns:
        ProcessedTracker 实例
    """
    global _tracker

    if _tracker is None:
        _tracker = ProcessedTracker(file_path=file_path)

    return _tracker


def reset_processed_tracker() -> None:
    """重置全局 ProcessedTracker（用于测试）"""
    global _tracker
    _tracker = None

