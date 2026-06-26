"""
通知器基类测试

测试 BaseNotifier, DummyNotifier 类。
"""

import pytest
from unittest.mock import MagicMock

from src.notifiers.base import BaseNotifier, DummyNotifier
from src.models import DailyReport


class TestDummyNotifier:
    """DummyNotifier 测试"""
    
    def test_init_with_reason(self):
        """初始化时指定原因"""
        notifier = DummyNotifier(reason="Test reason")
        
        assert notifier._reason == "Test reason"
    
    def test_init_default_reason(self):
        """默认原因"""
        notifier = DummyNotifier()
        
        assert notifier._reason == "未配置通知"
    
    @pytest.mark.asyncio
    async def test_send_daily_report_returns_true(self, sample_daily_report):
        """发送日报返回 True"""
        notifier = DummyNotifier()
        
        result = await notifier.send_daily_report(sample_daily_report)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_deep_analysis_returns_true(self):
        """发送深度分析返回 True"""
        notifier = DummyNotifier()
        
        result = await notifier.send_deep_analysis(
            paper_id="2501.12345",
            paper_title="Test Paper",
            summary="Test summary",
            issue_url="https://github.com/test/repo/issues/1",
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_close_no_error(self):
        """关闭不抛出异常"""
        notifier = DummyNotifier()
        
        await notifier.close()  # 不应抛出异常
    
    @pytest.mark.asyncio
    async def test_context_manager(self, sample_daily_report):
        """上下文管理器"""
        async with DummyNotifier() as notifier:
            result = await notifier.send_daily_report(sample_daily_report)
            assert result is True

