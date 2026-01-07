"""
LLM 异步统一客户端

基于 LangChain init_chat_model 实现多提供商 LLM 访问。
支持 with_structured_output 结构化输出。

所有消息接口使用 LangChain BaseMessage 类型，保证与 LangChain 生态一致。
"""

import asyncio
import logging
from collections.abc import Sequence
from typing import AsyncIterator, Type, TypeVar, Optional, Union

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage
from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel

from src.config import get_settings
from .providers import get_provider_config, get_structured_output_method
from .exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthError,
    LLMParseError,
)


T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM 异步统一客户端

    基于 LangChain init_chat_model 实现，自动选择最佳提供商客户端。
    所有消息接口使用 LangChain BaseMessage 类型。

    Usage:
        from langchain_core.messages import SystemMessage, HumanMessage

        async with LLMClient() as client:
            response = await client.chat([HumanMessage(content="Hello!")])
            print(response)

        # 或者不使用上下文管理器
        client = LLMClient()
        messages = [
            SystemMessage(content="你是一个助手"),
            HumanMessage(content="你好"),
        ]
        response = await client.chat(messages)
        await client.close()
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        """
        初始化 LLM 客户端

        Args:
            provider: 提供商名称，默认从配置系统读取
            model: 模型名称，默认从配置系统读取
            temperature: 温度参数，默认 0.7
            max_tokens: 最大 token 数，默认 None (使用模型默认)
            timeout: 请求超时(秒)，默认从配置系统读取
            max_retries: 最大重试次数，默认从配置系统读取

        Raises:
            ValueError: 当 provider 或 model 未配置时
        """
        settings = get_settings()

        # 获取提供商和模型（参数优先，否则从配置读取）
        self._provider = provider or settings.llm.provider
        self._model = model or settings.llm.model

        # 验证必填项
        if not self._provider:
            raise ValueError(
                "LLM provider 未配置，请在参数、配置文件或环境变量中设置"
            )
        if not self._model:
            raise ValueError(
                "LLM model 未配置，请在参数、配置文件或环境变量中设置"
            )

        # 获取提供商配置
        self._provider_config = get_provider_config(self._provider)

        # 获取 API Key
        self._api_key = settings.get_api_key()
        if not self._api_key:
            raise ValueError("API Key 未配置，请在配置文件或环境变量 LLM_API_KEY 中设置")

        # 设置参数
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout or settings.advanced.llm_timeout
        self._max_retries = max_retries or settings.advanced.llm_max_retries

        # 使用 init_chat_model 自动选择最佳客户端
        self._llm = self._create_llm()

    def _create_llm(self):
        """
        根据提供商创建对应的 LangChain Chat 模型

        使用 init_chat_model 自动选择：
        - openai -> ChatOpenAI
        - anthropic -> ChatAnthropic
        - gemini/google -> ChatGoogleGenerativeAI
        - 其他 OpenAI 兼容 -> ChatOpenAI with base_url
        """
        provider_lower = self._provider.lower()

        # 提供商到 LangChain model_provider 的映射
        provider_mapping = {
            "openai": "openai",
            "anthropic": "anthropic",
            "gemini": "google_genai",
            "google": "google_genai",
        }

        # 通用参数
        common_kwargs = {
            "model": self._model,
            "temperature": self._temperature,
            "max_retries": self._max_retries,
        }

        # 根据提供商配置特定参数
        if provider_lower in provider_mapping:
            model_provider = provider_mapping[provider_lower]

            # 各提供商的 API Key 参数名不同
            if model_provider == "openai":
                common_kwargs["api_key"] = self._api_key
                common_kwargs["timeout"] = self._timeout
                if self._max_tokens:
                    common_kwargs["max_tokens"] = self._max_tokens
            elif model_provider == "anthropic":
                common_kwargs["api_key"] = self._api_key
                common_kwargs["timeout"] = self._timeout
                if self._max_tokens:
                    common_kwargs["max_tokens"] = self._max_tokens
            elif model_provider == "google_genai":
                common_kwargs["google_api_key"] = self._api_key
                if self._max_tokens:
                    common_kwargs["max_output_tokens"] = self._max_tokens

            logger.debug(f"使用 {model_provider} 客户端: {self._model}")
            return init_chat_model(model_provider=model_provider, **common_kwargs)

        # OpenAI 兼容模式（OpenRouter, DeepSeek, Qwen 等）
        # DeepSeek reasoner 需要特殊处理
        if provider_lower == "deepseek":
            from .deepseek_reasoner import create_deepseek_client

            logger.debug(f"使用 DeepSeek 客户端: {self._model}")
            return create_deepseek_client(
                model=self._model,
                api_key=self._api_key,
                base_url=self._provider_config.base_url,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                timeout=self._timeout,
                max_retries=self._max_retries,
            )

        from langchain_openai import ChatOpenAI

        logger.debug(f"使用 OpenAI 兼容模式 ({provider_lower}): {self._model}")
        return ChatOpenAI(
            model=self._model,
            api_key=self._api_key,
            base_url=self._provider_config.base_url,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            timeout=self._timeout,
            max_retries=self._max_retries,
        )

    @property
    def provider(self) -> str:
        """当前提供商"""
        return self._provider

    @property
    def model(self) -> str:
        """当前模型"""
        return self._model

    @property
    def base_url(self) -> Optional[str]:
        """当前 API base URL (仅 OpenAI 兼容模式)"""
        return self._provider_config.base_url

    @property
    def api_key(self) -> str:
        """当前 API Key（脱敏显示）"""
        if len(self._api_key) > 8:
            return f"{self._api_key[:4]}...{self._api_key[-4:]}"
        return "***"

    def get_langchain_client(self):
        """
        获取底层 LangChain Chat 模型实例

        用于需要直接访问 LangChain 功能的场景，如：
        - bind_tools() 绑定工具
        - create_react_agent() 创建 Agent
        - 其他 LangChain 原生功能

        Returns:
            BaseChatModel: LangChain Chat 模型实例
        """
        return self._llm

    async def chat(
        self,
        messages: Sequence[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        异步聊天接口

        Args:
            messages: LangChain 消息列表 (SystemMessage, HumanMessage, AIMessage)
            temperature: 温度参数，默认使用实例配置
            max_tokens: 最大 token 数，默认使用实例配置

        Returns:
            LLM 响应文本

        Raises:
            LLMError: LLM 调用失败时
        """
        try:
            # 如果需要覆盖参数，创建临时 LLM 实例
            if temperature is not None or max_tokens is not None:
                bind_kwargs = {}
                if temperature is not None:
                    bind_kwargs["temperature"] = temperature
                if max_tokens is not None:
                    # 根据提供商使用不同的参数名
                    if self._provider.lower() in ("gemini", "google"):
                        bind_kwargs["max_output_tokens"] = max_tokens
                    else:
                        bind_kwargs["max_tokens"] = max_tokens
                llm = self._llm.bind(**bind_kwargs)
            else:
                llm = self._llm

            response = await llm.ainvoke(list(messages))
            return str(response.content)

        except Exception as e:
            raise self._convert_exception(e)

    async def chat_structured(
        self,
        messages: Sequence[BaseMessage],
        schema: Type[T],
        max_retries: Optional[int] = None,
        method: Optional[str] = None,
    ) -> T:
        """
        异步结构化聊天接口

        根据提供商和模型自动选择最佳结构化输出方式。
        优先级: json_schema > function_calling > json_mode

        Args:
            messages: LangChain 消息列表
            schema: Pydantic 模型类
            max_retries: 最大重试次数，默认使用实例配置
            method: 强制指定结构化输出方式 (json_schema/function_calling/json_mode)
                    默认自动根据模型选择

        Returns:
            Pydantic 模型实例

        Raises:
            LLMParseError: JSON 解析失败时
            LLMError: LLM 调用失败时
        """
        retries = max_retries if max_retries is not None else self._max_retries

        # 根据提供商和模型自动选择结构化输出方式
        if method is None:
            method = get_structured_output_method(self._provider, self._model)
            logger.debug(
                f"自动选择结构化输出方式: {method} "
                f"(provider={self._provider}, model={self._model})"
            )

        # 使用选定的方式创建结构化输出
        structured_llm = self._llm.with_structured_output(schema, method=method)

        last_error: Optional[Exception] = None

        for attempt in range(retries + 1):
            try:
                result = await structured_llm.ainvoke(list(messages))
                return result

            except OutputParserException as e:
                last_error = e
                if attempt < retries:
                    logger.warning(
                        f"结构化输出解析失败，重试 {attempt + 1}/{retries + 1}: {e}"
                    )
                    await asyncio.sleep(0.5)
                    continue

            except Exception as e:
                raise self._convert_exception(e)

        raise LLMParseError(
            f"结构化输出解析失败 (尝试 {retries + 1} 次): {last_error}",
            raw_response=str(last_error) if last_error else "",
        )

    async def chat_stream(
        self,
        messages: Sequence[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        异步流式聊天接口

        Args:
            messages: LangChain 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数

        Yields:
            逐 token 输出的字符串
        """
        try:
            # 如果需要覆盖参数，创建临时 LLM 实例
            if temperature is not None or max_tokens is not None:
                bind_kwargs = {}
                if temperature is not None:
                    bind_kwargs["temperature"] = temperature
                if max_tokens is not None:
                    if self._provider.lower() in ("gemini", "google"):
                        bind_kwargs["max_output_tokens"] = max_tokens
                    else:
                        bind_kwargs["max_tokens"] = max_tokens
                llm = self._llm.bind(**bind_kwargs)
            else:
                llm = self._llm

            async for chunk in llm.astream(list(messages)):
                if chunk.content:
                    yield str(chunk.content)

        except Exception as e:
            raise self._convert_exception(e)

    def _convert_exception(self, e: Exception) -> LLMError:
        """
        将各种异常转换为统一的 LLM 异常

        Args:
            e: 原始异常

        Returns:
            对应的 LLMError 子类
        """
        error_msg = str(e).lower()

        if "rate" in error_msg and "limit" in error_msg:
            return LLMRateLimitError(str(e))
        elif "quota" in error_msg or "resource exhausted" in error_msg:
            return LLMRateLimitError(str(e))
        elif "timeout" in error_msg or "timed out" in error_msg or "deadline" in error_msg:
            return LLMTimeoutError(str(e))
        elif "auth" in error_msg or "api key" in error_msg or "unauthorized" in error_msg or "unauthenticated" in error_msg:
            return LLMAuthError(str(e))
        else:
            return LLMError(str(e))

    async def close(self) -> None:
        """关闭客户端，释放资源"""
        # LangChain Chat 模型不需要显式关闭
        pass

    async def __aenter__(self) -> "LLMClient":
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口"""
        await self.close()
