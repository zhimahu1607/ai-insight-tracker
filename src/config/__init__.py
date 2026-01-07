"""
配置系统

提供统一的配置管理能力，支持多来源配置加载和优先级管理。

配置优先级：config/settings.yaml > 环境变量 > 默认值

Usage:
    from src.config import get_settings

    settings = get_settings()
    settings.llm.provider  # "deepseek"
    settings.get_api_key()  # API Key
"""

from .models import (
    AdvancedConfig,
    AnalysisConfig,
    ArxivConfig,
    LLMConfig,
    NotificationConfig,
    PDFConfig,
    SearchConfig,
    Settings,
)
from .loader import (
    get_settings,
    load_settings,
    load_settings_without_validation,
    reload_settings,
)
from .check import (
    check_first_run,
    check_required_config,
    ensure_config,
    ensure_config_or_exit,
)

__all__ = [
    # 配置模型
    "Settings",
    "LLMConfig",
    "ArxivConfig",
    "SearchConfig",
    "AnalysisConfig",
    "NotificationConfig",
    "PDFConfig",
    "AdvancedConfig",
    # 配置加载
    "get_settings",
    "load_settings",
    "load_settings_without_validation",
    "reload_settings",
    # 配置检查
    "check_first_run",
    "check_required_config",
    "ensure_config",
    "ensure_config_or_exit",
]
