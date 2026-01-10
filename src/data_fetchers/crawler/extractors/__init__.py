"""
提取器注册表

根据公司标识符返回对应的提取器实例。
"""

from ..base import BaseExtractor
from .anthropic import AnthropicExtractor
from .claude import ClaudeExtractor
from .cursor import CursorExtractor
from .deepseek import DeepSeekExtractor
from .deepmind import DeepMindExtractor
from .gemini import GeminiExtractor
from .google_research import GoogleResearchExtractor
from .qwen import QwenExtractor


# 提取器注册表
_EXTRACTORS: dict[str, type[BaseExtractor]] = {
    "anthropic": AnthropicExtractor,
    "claude": ClaudeExtractor,
    "cursor": CursorExtractor,
    "deepseek": DeepSeekExtractor,
    "deepmind": DeepMindExtractor,
    "gemini": GeminiExtractor,
    "google_research": GoogleResearchExtractor,
    "qwen": QwenExtractor,
}


def get_extractor(name: str) -> BaseExtractor:
    """
    获取提取器实例

    Args:
        name: 公司标识符或提取器名称

    Returns:
        提取器实例

    Raises:
        ValueError: 未知的提取器名称
    """
    extractor_cls = _EXTRACTORS.get(name.lower())
    if extractor_cls is None:
        raise ValueError(f"未知的提取器: {name}")
    return extractor_cls()


def list_extractors() -> list[str]:
    """返回所有可用的提取器名称"""
    return list(_EXTRACTORS.keys())

