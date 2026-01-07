"""
全局共享资源

提供全局共享的 LLM 并发控制信号量，确保论文分析和热点分析
同时运行时总并发数不超过配置上限。
"""

import asyncio
from typing import Optional

from src.config import get_settings


_global_llm_semaphore: Optional[asyncio.Semaphore] = None


def get_llm_semaphore() -> asyncio.Semaphore:
    """
    获取全局 LLM 并发控制信号量（单例）

    论文分析和热点分析模块共享同一个 Semaphore 实例，
    确保总并发数不超过配置的 analysis.max_concurrent 上限。

    Returns:
        asyncio.Semaphore: 全局共享的信号量实例
    """
    global _global_llm_semaphore
    if _global_llm_semaphore is None:
        settings = get_settings()
        _global_llm_semaphore = asyncio.Semaphore(settings.analysis.max_concurrent)
    return _global_llm_semaphore


def reset_llm_semaphore() -> None:
    """
    重置全局 LLM 信号量（仅用于测试）

    在测试环境中可能需要重置信号量以确保测试隔离。
    """
    global _global_llm_semaphore
    _global_llm_semaphore = None

