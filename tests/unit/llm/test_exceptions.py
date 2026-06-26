"""
LLM 异常测试

测试 LLMError 及其子类。
"""

import pytest

from src.llm.exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthError,
    LLMParseError,
)


class TestLLMError:
    """LLMError 基类测试"""
    
    def test_can_raise(self):
        """可以抛出"""
        with pytest.raises(LLMError):
            raise LLMError("Test error")
    
    def test_message(self):
        """错误消息正确"""
        try:
            raise LLMError("Test message")
        except LLMError as e:
            assert str(e) == "Test message"


class TestLLMRateLimitError:
    """LLMRateLimitError 测试"""
    
    def test_inheritance(self):
        """继承自 LLMError"""
        error = LLMRateLimitError()
        assert isinstance(error, LLMError)
    
    def test_default_message(self):
        """默认消息"""
        error = LLMRateLimitError()
        assert "频率超限" in str(error)
    
    def test_custom_message(self):
        """自定义消息"""
        error = LLMRateLimitError("Custom rate limit message")
        assert str(error) == "Custom rate limit message"
    
    def test_retry_after_default(self):
        """retry_after 默认值"""
        error = LLMRateLimitError()
        assert error.retry_after == 0
    
    def test_retry_after_custom(self):
        """自定义 retry_after"""
        error = LLMRateLimitError(retry_after=30)
        assert error.retry_after == 30


class TestLLMTimeoutError:
    """LLMTimeoutError 测试"""
    
    def test_inheritance(self):
        """继承自 LLMError"""
        error = LLMTimeoutError("Timeout")
        assert isinstance(error, LLMError)
    
    def test_message(self):
        """错误消息"""
        error = LLMTimeoutError("Request timed out after 60s")
        assert "60s" in str(error)


class TestLLMAuthError:
    """LLMAuthError 测试"""
    
    def test_inheritance(self):
        """继承自 LLMError"""
        error = LLMAuthError("Invalid API key")
        assert isinstance(error, LLMError)


class TestLLMParseError:
    """LLMParseError 测试"""
    
    def test_inheritance(self):
        """继承自 LLMError"""
        error = LLMParseError("Parse failed")
        assert isinstance(error, LLMError)
    
    def test_raw_response_default(self):
        """raw_response 默认值"""
        error = LLMParseError("Parse failed")
        assert error.raw_response == ""
    
    def test_raw_response_custom(self):
        """自定义 raw_response"""
        error = LLMParseError("Parse failed", raw_response='{"invalid": json}')
        assert error.raw_response == '{"invalid": json}'

