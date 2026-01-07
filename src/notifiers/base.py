"""
通知器基类

定义通知器的抽象接口，支持异步操作和上下文管理。
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from src.models import DailyReport


logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """
    通知器抽象基类

    定义通知器的标准接口，所有具体通知器实现都应继承此类。

    Usage:
        async with SomeNotifier() as notifier:
            await notifier.send_daily_report(report)
            await notifier.send_deep_analysis(paper_id, title, summary, issue_url)
    """

    @abstractmethod
    async def send_daily_report(self, report: DailyReport) -> bool:
        """
        发送每日报告

        Args:
            report: DailyReport 实例

        Returns:
            发送是否成功
        """
        pass

    @abstractmethod
    async def send_deep_analysis(
        self,
        paper_id: str,
        paper_title: str,
        summary: str,
        issue_url: str,
    ) -> bool:
        """
        发送深度分析结果通知

        Args:
            paper_id: 论文 ID
            paper_title: 论文标题
            summary: 分析摘要（截取前 500 字）
            issue_url: GitHub Issue 链接

        Returns:
            发送是否成功
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭通知器，释放资源"""
        pass

    async def __aenter__(self) -> "BaseNotifier":
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口"""
        await self.close()


class DummyNotifier(BaseNotifier):
    """
    空通知器

    用于未配置通知或测试场景，不执行实际发送操作。
    """

    def __init__(self, reason: Optional[str] = None):
        """
        初始化空通知器

        Args:
            reason: 使用空通知器的原因（用于日志）
        """
        self._reason = reason or "未配置通知"

    async def send_daily_report(self, report: DailyReport) -> bool:
        """跳过发送，记录日志"""
        logger.info(
            f"跳过每日报告通知 ({self._reason}): "
            f"{report.date}, 论文 {report.paper_count} 篇, 热点 {report.news_count} 条"
        )
        return True

    async def send_deep_analysis(
        self,
        paper_id: str,
        paper_title: str,
        summary: str,
        issue_url: str,
    ) -> bool:
        """跳过发送，记录日志"""
        logger.info(
            f"跳过深度分析通知 ({self._reason}): [{paper_id}] {paper_title}"
        )
        return True

    async def close(self) -> None:
        """无需关闭操作"""
        pass

