"""
统一的 Prompt 加载器

集中管理所有 Agent 的 Prompt，从 Python 模块加载。
"""

import logging
from typing import Optional

from src.prompts import (
    # Paper prompts
    paper_light_system_prompt,
    paper_light_user_prompt,
    paper_supervisor_prompt,
    paper_researcher_prompt,
    paper_writer_prompt,
    paper_reviewer_prompt,
    # News prompts
    news_light_system_prompt,
    news_light_user_prompt,
)


logger = logging.getLogger(__name__)


class PromptLoadError(Exception):
    """Prompt 加载错误"""
    pass


# Prompt 注册表
_PROMPT_REGISTRY: dict[str, str] = {
    # Paper - Light Analyzer
    "paper.light.system": paper_light_system_prompt,
    "paper.light.user": paper_light_user_prompt,
    # Paper - Deep Analyzer
    "paper.deep_analyzer.supervisor": paper_supervisor_prompt,
    "paper.deep_analyzer.researcher": paper_researcher_prompt,
    "paper.deep_analyzer.writer": paper_writer_prompt,
    "paper.deep_analyzer.reviewer": paper_reviewer_prompt,
    # News - Light Analyzer
    "news.light.system": news_light_system_prompt,
    "news.light.user": news_light_user_prompt,
}


class PromptLoader:
    """
    统一的 Prompt 加载器

    从 Python 模块加载 Prompt，提供统一的访问接口。

    Usage:
        # 加载 paper 模块的 light analyzer system prompt
        prompt = PromptLoader.load("paper", "light", "system")

        # 加载 paper 模块的 deep analyzer researcher prompt
        prompt = PromptLoader.load("paper", "deep_analyzer", "researcher")

        # 加载 system/user prompt 对
        system, user = PromptLoader.load_pair("paper", "light")
    """

    @classmethod
    def load(
        cls,
        module: str,
        category: str,
        name: str,
        default: Optional[str] = None,
    ) -> str:
        """
        加载指定的 Prompt

        Args:
            module: 模块名 ("paper" 或 "news")
            category: 类别 ("light" 或 "deep_analyzer")
            name: Prompt 名称 ("system", "user", "researcher", "reviewer" 等)
            default: 默认值，当 Prompt 不存在时返回

        Returns:
            Prompt 内容字符串

        Raises:
            PromptLoadError: 当 Prompt 不存在且未提供默认值时
        """
        key = f"{module}.{category}.{name}"
        prompt = _PROMPT_REGISTRY.get(key)

        if prompt is None:
            if default is not None:
                logger.warning(f"Prompt 不存在: {key}，使用默认值")
                return default
            raise PromptLoadError(f"Prompt 不存在: {key}")

        return prompt

    @classmethod
    def load_pair(
        cls,
        module: str,
        category: str,
        default_system: Optional[str] = None,
        default_user: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        加载 system 和 user Prompt 对

        便捷方法，用于加载浅度分析器常用的 system/user prompt 对。

        Args:
            module: 模块名 ("paper" 或 "news")
            category: 类别 ("light")
            default_system: system prompt 默认值
            default_user: user prompt 默认值

        Returns:
            tuple: (system_prompt, user_prompt)
        """
        system_prompt = cls.load(module, category, "system", default_system)
        user_prompt = cls.load(module, category, "user", default_user)
        return system_prompt, user_prompt
