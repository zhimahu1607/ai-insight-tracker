"""
全局共享资源测试

测试 LLM 信号量管理。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from src.agents.shared import get_llm_semaphore, reset_llm_semaphore


class TestGetLLMSemaphore:
    """get_llm_semaphore 函数测试"""
    
    def test_returns_semaphore(self, mock_settings):
        """返回 Semaphore 实例"""
        reset_llm_semaphore()
        
        with patch("src.agents.shared.get_settings", return_value=mock_settings):
            semaphore = get_llm_semaphore()
        
        assert isinstance(semaphore, asyncio.Semaphore)
    
    def test_singleton(self, mock_settings):
        """单例模式"""
        reset_llm_semaphore()
        
        with patch("src.agents.shared.get_settings", return_value=mock_settings):
            sem1 = get_llm_semaphore()
            sem2 = get_llm_semaphore()
        
        assert sem1 is sem2
    
    def test_max_concurrent_from_settings(self, mock_settings):
        """并发数来自配置"""
        reset_llm_semaphore()
        mock_settings.analysis.max_concurrent = 3
        
        with patch("src.agents.shared.get_settings", return_value=mock_settings):
            semaphore = get_llm_semaphore()
        
        # Semaphore 的 _value 属性表示当前可用数量
        assert semaphore._value == 3


class TestResetLLMSemaphore:
    """reset_llm_semaphore 函数测试"""
    
    def test_reset_clears_singleton(self, mock_settings):
        """重置清除单例"""
        with patch("src.agents.shared.get_settings", return_value=mock_settings):
            sem1 = get_llm_semaphore()
            reset_llm_semaphore()
            sem2 = get_llm_semaphore()
        
        # 重置后应该是新实例
        assert sem1 is not sem2

