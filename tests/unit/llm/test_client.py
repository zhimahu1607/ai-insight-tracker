"""
LLM 客户端测试

测试 LLMClient 类的各种功能。
基于 LangChain 实现，需要 Mock LangChain 调用。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.llm.client import LLMClient
from src.llm.exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthError,
    LLMParseError,
)


class SampleSchema(BaseModel):
    """测试用 Schema"""
    name: str
    value: int


class TestLLMClientInit:
    """LLMClient 初始化测试"""
    
    def test_init_from_settings(self, mock_settings):
        """从配置初始化"""
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            with patch("langchain_openai.ChatOpenAI"):
                client = LLMClient()
        
        assert client.provider == "deepseek"
        assert client.model == "deepseek-chat"
    
    def test_init_with_params(self, mock_settings):
        """使用参数覆盖配置"""
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            with patch("langchain_openai.ChatOpenAI"):
                client = LLMClient(
                    provider="openai",
                    model="gpt-4",
                )
        
        assert client.provider == "openai"
        assert client.model == "gpt-4"
    
    def test_init_missing_provider(self, mock_settings):
        """缺少 provider 时抛出 ValueError"""
        mock_settings.llm.provider = ""
        
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            with pytest.raises(ValueError, match="provider 未配置"):
                LLMClient()
    
    def test_init_missing_api_key(self, mock_settings):
        """缺少 API Key 时抛出 ValueError"""
        mock_settings.llm.api_key = ""
        
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            with pytest.raises(ValueError, match="API Key 未配置"):
                LLMClient()


class TestLLMClientProperties:
    """LLMClient 属性测试"""
    
    def test_provider_property(self, mock_settings):
        """provider 属性"""
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            with patch("langchain_openai.ChatOpenAI"):
                client = LLMClient()
        
        assert client.provider == "deepseek"
    
    def test_model_property(self, mock_settings):
        """model 属性"""
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            with patch("langchain_openai.ChatOpenAI"):
                client = LLMClient()
        
        assert client.model == "deepseek-chat"
    
    def test_api_key_masked(self, mock_settings):
        """API Key 脱敏显示"""
        mock_settings.llm.api_key = "sk-1234567890abcdef"
        
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            with patch("langchain_openai.ChatOpenAI"):
                client = LLMClient()
        
        # 应该只显示前 4 位和后 4 位
        assert client.api_key == "sk-1...cdef"
    
    def test_api_key_short(self, mock_settings):
        """短 API Key 完全隐藏"""
        mock_settings.llm.api_key = "short"
        
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            with patch("langchain_openai.ChatOpenAI"):
                client = LLMClient()
        
        assert client.api_key == "***"


class TestLLMClientChat:
    """LLMClient.chat 方法测试"""
    
    @pytest.mark.asyncio
    async def test_chat_success(self, mock_settings):
        """正常聊天请求"""
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            # deepseek provider 使用 create_deepseek_client（延迟导入）
            with patch("src.llm.deepseek_reasoner.create_deepseek_client") as mock_create_client:
                # 设置 Mock 响应
                mock_response = MagicMock()
                mock_response.content = "Hello, world!"
                
                mock_llm = MagicMock()
                mock_llm.ainvoke = AsyncMock(return_value=mock_response)
                mock_create_client.return_value = mock_llm
                
                client = LLMClient()
                response = await client.chat([
                    HumanMessage(content="Hi")
                ])
        
        # ✅ 验证 LangChain LLM 被调用
        mock_llm.ainvoke.assert_called_once()
        
        assert response == "Hello, world!"
    
    @pytest.mark.asyncio
    async def test_chat_rate_limit_error(self, mock_settings):
        """RateLimitError 转换"""
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            # deepseek provider 使用 create_deepseek_client（延迟导入）
            with patch("src.llm.deepseek_reasoner.create_deepseek_client") as mock_create_client:
                mock_llm = MagicMock()
                mock_llm.ainvoke = AsyncMock(
                    side_effect=Exception("Rate limit exceeded")
                )
                mock_create_client.return_value = mock_llm
                
                client = LLMClient()
                
                with pytest.raises(LLMRateLimitError):
                    await client.chat([HumanMessage(content="Hi")])
    
    @pytest.mark.asyncio
    async def test_chat_timeout_error(self, mock_settings):
        """TimeoutError 转换"""
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            # deepseek provider 使用 create_deepseek_client（延迟导入）
            with patch("src.llm.deepseek_reasoner.create_deepseek_client") as mock_create_client:
                mock_llm = MagicMock()
                mock_llm.ainvoke = AsyncMock(
                    side_effect=Exception("Request timed out")
                )
                mock_create_client.return_value = mock_llm
                
                client = LLMClient()
                
                with pytest.raises(LLMTimeoutError):
                    await client.chat([HumanMessage(content="Hi")])
    
    @pytest.mark.asyncio
    async def test_chat_auth_error(self, mock_settings):
        """AuthenticationError 转换"""
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            # deepseek provider 使用 create_deepseek_client（延迟导入）
            with patch("src.llm.deepseek_reasoner.create_deepseek_client") as mock_create_client:
                mock_llm = MagicMock()
                mock_llm.ainvoke = AsyncMock(
                    side_effect=Exception("Invalid API key unauthorized")
                )
                mock_create_client.return_value = mock_llm
                
                client = LLMClient()
                
                with pytest.raises(LLMAuthError):
                    await client.chat([HumanMessage(content="Hi")])


class TestLLMClientContextManager:
    """LLMClient 上下文管理器测试"""
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_settings):
        """异步上下文管理器"""
        with patch("src.llm.client.get_settings", return_value=mock_settings):
            with patch("langchain_openai.ChatOpenAI") as mock_chat_openai:
                mock_llm = MagicMock()
                mock_chat_openai.return_value = mock_llm
                
                async with LLMClient() as client:
                    assert client is not None
