"""
LLM 提供商配置

定义支持的 LLM 提供商及其配置信息。
包含结构化输出方式的配置，优先级：json_schema > function_calling > json_mode
"""

import re
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


# 结构化输出方式类型
StructuredOutputMethod = Literal["json_schema", "function_calling", "json_mode"]


class LLMProvider(str, Enum):
    """支持的 LLM 提供商"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    GEMINI = "gemini"
    ZHIPU = "zhipu"
    GROK = "grok"


class ProviderConfig(BaseModel):
    """提供商配置"""

    provider: LLMProvider
    base_url: str = Field(description="API Base URL (用于 OpenAI 兼容客户端)")
    # 默认结构化输出方式（按优先级: json_schema > function_calling > json_mode）
    default_structured_method: StructuredOutputMethod = Field(
        default="function_calling",
        description="默认结构化输出方式"
    )
    # 是否支持 json_schema (Structured Outputs)
    supports_json_schema: bool = Field(
        default=False,
        description="是否支持 json_schema 结构化输出"
    )
    # 是否支持 function_calling (Tool Use)
    supports_function_calling: bool = Field(
        default=True,
        description="是否支持 function_calling"
    )
    # 是否支持 json_mode
    supports_json_mode: bool = Field(
        default=True,
        description="是否支持 json_mode"
    )


# 提供商配置表
# 结构化输出优先级: json_schema > function_calling > json_mode
PROVIDER_CONFIGS: dict[str, ProviderConfig] = {
    "openai": ProviderConfig(
        provider=LLMProvider.OPENAI,
        base_url="https://api.openai.com/v1",
        # OpenAI: GPT-4o+ 支持 json_schema，其他支持 function_calling
        default_structured_method="function_calling",
        supports_json_schema=True,  # GPT-4o-mini, GPT-4o-2024-08-06+ 支持
        supports_function_calling=True,
        supports_json_mode=True,
    ),
    "anthropic": ProviderConfig(
        provider=LLMProvider.ANTHROPIC,
        base_url="https://api.anthropic.com/v1",
        # Anthropic: 仅支持 tool_use (function_calling)
        default_structured_method="function_calling",
        supports_json_schema=False,
        supports_function_calling=True,
        supports_json_mode=False,  # Claude 不支持 json_mode
    ),
    "openrouter": ProviderConfig(
        provider=LLMProvider.OPENROUTER,
        base_url="https://openrouter.ai/api/v1",
        # OpenRouter: 能力取决于底层模型，默认使用 function_calling
        default_structured_method="function_calling",
        supports_json_schema=False,
        supports_function_calling=True,
        supports_json_mode=True,
    ),
    "deepseek": ProviderConfig(
        provider=LLMProvider.DEEPSEEK,
        base_url="https://api.deepseek.com/v1",
        # DeepSeek: deepseek-chat 支持 function_calling，reasoner 不支持
        default_structured_method="function_calling",
        supports_json_schema=False,
        supports_function_calling=True,  # 仅 deepseek-chat/coder
        supports_json_mode=True,
    ),
    "qwen": ProviderConfig(
        provider=LLMProvider.QWEN,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        # Qwen: 支持 function_calling 和 json_mode
        default_structured_method="function_calling",
        supports_json_schema=False,
        supports_function_calling=True,
        supports_json_mode=True,
    ),
    "gemini": ProviderConfig(
        provider=LLMProvider.GEMINI,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        # Gemini: 1.5 Pro+ 支持 controlled generation (json_schema)
        default_structured_method="function_calling",
        supports_json_schema=True,  # Gemini 1.5 Pro+ 支持
        supports_function_calling=True,
        supports_json_mode=True,
    ),
    "zhipu": ProviderConfig(
        provider=LLMProvider.ZHIPU,
        base_url="https://open.bigmodel.cn/api/paas/v4",
        # 智谱 GLM: GLM-4 支持 function_calling
        default_structured_method="function_calling",
        supports_json_schema=False,
        supports_function_calling=True,
        supports_json_mode=True,
    ),
    "grok": ProviderConfig(
        provider=LLMProvider.GROK,
        base_url="https://api.x.ai/v1",
        # Grok: 支持 function_calling 和 json_mode
        default_structured_method="function_calling",
        supports_json_schema=False,
        supports_function_calling=True,
        supports_json_mode=True,
    ),
}


# 处理 GitHub Actions / 环境变量里常见的“不可见字符”问题：
# - 末尾空格/换行
# - 全角空格
# - 零宽字符 (ZWSP/ZWNJ/ZWJ) 与 BOM
_INVISIBLE_CHARS_RE = re.compile(r"[\s\u3000\u200b\u200c\u200d\ufeff]+")


def normalize_provider_name(provider: str) -> str:
    """
    规范化 provider 名称，用于字典 key 匹配。

    说明：
    - GitHub Variables 有时会被误复制进尾部换行或不可见空格，导致看起来是 "deepseek"
      但实际是 "deepseek\\n" / "deepseek "，从而匹配失败。
    """
    if provider is None:
        return ""
    # 去除空白与常见不可见字符，再做大小写归一
    cleaned = _INVISIBLE_CHARS_RE.sub("", str(provider))
    return cleaned.strip().casefold()



# 不支持 function_calling 的模型模式列表
# 这些模型只能使用 json_mode
_NO_FUNCTION_CALLING_PATTERNS: list[re.Pattern] = [
    re.compile(r"deepseek-reasoner", re.IGNORECASE),
    re.compile(r"deepseek-r1", re.IGNORECASE),
    re.compile(r"o1-preview", re.IGNORECASE),  # OpenAI o1 系列
    re.compile(r"o1-mini", re.IGNORECASE),
    re.compile(r"o3-mini", re.IGNORECASE),
]

# 支持 json_schema 的模型模式列表 (最高优先级)
_JSON_SCHEMA_PATTERNS: list[re.Pattern] = [
    re.compile(r"gpt-4o-mini", re.IGNORECASE),
    re.compile(r"gpt-4o-2024-08-06", re.IGNORECASE),
    re.compile(r"gpt-4o-2024-11", re.IGNORECASE),
    re.compile(r"gpt-4o-2025", re.IGNORECASE),
    re.compile(r"gemini-1\.5-pro", re.IGNORECASE),
    re.compile(r"gemini-2\.0", re.IGNORECASE),
]


def get_provider_config(provider: str) -> ProviderConfig:
    """
    获取提供商配置

    Args:
        provider: 提供商名称

    Returns:
        ProviderConfig 实例

    Raises:
        ValueError: 提供商不支持时
    """
    provider_lower = normalize_provider_name(provider)
    if provider_lower not in PROVIDER_CONFIGS:
        supported = ", ".join(PROVIDER_CONFIGS.keys())
        raise ValueError(
            f"不支持的 LLM 提供商: {provider}。支持的提供商: {supported}"
        )
    return PROVIDER_CONFIGS[provider_lower]


def get_structured_output_method(
    provider: str,
    model: str,
) -> StructuredOutputMethod:
    """
    根据提供商和模型确定最佳结构化输出方式

    优先级: json_schema > function_calling > json_mode

    Args:
        provider: 提供商名称
        model: 模型名称

    Returns:
        最佳结构化输出方式
    """
    config = get_provider_config(provider)

    # 1. 检查是否为不支持 function_calling 的特殊模型
    for pattern in _NO_FUNCTION_CALLING_PATTERNS:
        if pattern.search(model):
            # 这些模型只能使用 json_mode
            if config.supports_json_mode:
                return "json_mode"
            # 如果连 json_mode 都不支持（如 Anthropic），回退到 function_calling
            # 实际上这类模型不应该配合 Anthropic 使用
            return "function_calling"

    # 2. 检查是否支持 json_schema（最高优先级）
    if config.supports_json_schema:
        for pattern in _JSON_SCHEMA_PATTERNS:
            if pattern.search(model):
                return "json_schema"

    # 3. 检查是否支持 function_calling（次优先级）
    if config.supports_function_calling:
        return "function_calling"

    # 4. 回退到 json_mode（最低优先级）
    if config.supports_json_mode:
        return "json_mode"

    # 5. 默认使用配置中的方式
    return config.default_structured_method
