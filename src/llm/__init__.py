"""
LLM 客户端模块

提供统一的多提供商 LLM 异步访问接口。
基于 LangChain init_chat_model 实现，支持 with_structured_output 结构化输出。

支持的提供商:
- OpenAI: 使用 langchain-openai (ChatOpenAI)
- Anthropic: 使用 langchain-anthropic (ChatAnthropic)
- Gemini/Google: 使用 langchain-google-genai (ChatGoogleGenerativeAI)
- 其他 OpenAI 兼容 API: 使用 langchain-openai + base_url

Usage:
    from src.llm import LLMClient, quick_chat, quick_structured, create_messages
    from langchain_core.messages import SystemMessage, HumanMessage

    # 方式 1: 使用上下文管理器
    async with LLMClient() as client:
        response = await client.chat([HumanMessage(content="Hello!")])

    # 方式 2: 快速聊天
    response = await quick_chat([HumanMessage(content="Hello!")])

    # 方式 3: 使用 create_messages 辅助函数
    messages = create_messages(system="你是助手", user="你好")
    response = await quick_chat(messages)

    # 方式 4: 快速结构化输出
    result = await quick_structured([...], MySchema)
"""

from collections.abc import Sequence
from typing import Type, TypeVar, Optional, Union

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
)
from pydantic import BaseModel

from .client import LLMClient
from .providers import LLMProvider, ProviderConfig, get_provider_config, PROVIDER_CONFIGS
from .exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthError,
    LLMParseError,
)


T = TypeVar("T", bound=BaseModel)


def create_messages(
    system: Optional[str] = None,
    user: Optional[str] = None,
    assistant: Optional[str] = None,
) -> list[BaseMessage]:
    """
    快速创建 LangChain 消息列表

    用于简化消息构建，按 system -> user -> assistant 顺序创建消息。

    Args:
        system: 系统消息内容
        user: 用户消息内容
        assistant: 助手消息内容

    Returns:
        LangChain BaseMessage 列表

    Usage:
        # 简单的用户消息
        messages = create_messages(user="你好")

        # 带系统提示的对话
        messages = create_messages(
            system="你是一个专业的AI助手",
            user="请帮我分析这篇论文",
        )

        # 完整的对话上下文
        messages = create_messages(
            system="你是助手",
            user="你好",
            assistant="你好！有什么可以帮你的？",
        )
    """
    messages: list[BaseMessage] = []

    if system:
        messages.append(SystemMessage(content=system))
    if user:
        messages.append(HumanMessage(content=user))
    if assistant:
        messages.append(AIMessage(content=assistant))

    return messages


async def quick_chat(
    messages: Sequence[BaseMessage],
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """
    快速聊天，自动管理客户端生命周期

    Args:
        messages: LangChain 消息列表
        provider: 提供商名称
        model: 模型名称

    Returns:
        LLM 响应文本
    """
    async with LLMClient(provider=provider, model=model) as client:
        return await client.chat(messages)


async def quick_structured(
    messages: Sequence[BaseMessage],
    schema: Type[T],
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> T:
    """
    快速结构化输出，自动管理客户端生命周期

    使用 LangChain with_structured_output 实现结构化输出。

    Args:
        messages: LangChain 消息列表
        schema: Pydantic 模型类
        provider: 提供商名称
        model: 模型名称

    Returns:
        Pydantic 模型实例
    """
    async with LLMClient(provider=provider, model=model) as client:
        return await client.chat_structured(messages, schema)


__all__ = [
    # 客户端
    "LLMClient",
    # 快捷函数
    "quick_chat",
    "quick_structured",
    "create_messages",
    # 消息类型 (re-export from langchain)
    "BaseMessage",
    "SystemMessage",
    "HumanMessage",
    "AIMessage",
    # 提供商
    "LLMProvider",
    "ProviderConfig",
    "get_provider_config",
    "PROVIDER_CONFIGS",
    # 异常
    "LLMError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMAuthError",
    "LLMParseError",
]
