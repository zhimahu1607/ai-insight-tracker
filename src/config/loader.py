"""
配置加载器

实现配置优先级：config/settings.yaml > 环境变量 > 默认值
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

from .models import Settings


# 环境变量到配置路径的映射
ENV_MAPPING: dict[str, str] = {
    # LLM 配置
    "LLM_PROVIDER": "llm.provider",
    "LLM_MODEL": "llm.model",
    "LLM_API_KEY": "llm.api_key",
    # arXiv 配置
    "CATEGORIES": "arxiv.categories",
    "ARXIV_MAX_RESULTS": "arxiv.max_results",
    "ARXIV_MAX_PAGES": "arxiv.max_pages",
    "ARXIV_REQUEST_DELAY": "arxiv.request_delay",
    # 搜索配置
    "SEARCH_API": "search.api",
    "TAVILY_API_KEY": "search.tavily_api_key",
    "SEARCH_MAX_RESULTS": "search.max_results",
    "SEARCH_TIMEOUT": "search.timeout",
    # 分析配置
    "ANALYSIS_MAX_CONCURRENT": "analysis.max_concurrent",
    "ANALYSIS_TIMEOUT": "analysis.timeout",
    "MAX_RESEARCH_ITERATIONS": "analysis.max_research_iterations",
    "MAX_WRITE_ITERATIONS": "analysis.max_write_iterations",
    # 通知配置
    "FEISHU_WEBHOOK_URL": "notification.feishu_webhook_url",
    "LANGUAGE": "notification.language",
    "FEISHU_MAX_PAPERS": "notification.max_papers",
    "FEISHU_MAX_NEWS": "notification.max_news",
    "FEISHU_TIMEOUT": "notification.timeout",
    "FEISHU_MAX_RETRIES": "notification.max_retries",
    # 高级配置
    "LLM_TIMEOUT": "advanced.llm_timeout",
    "LLM_MAX_RETRIES": "advanced.llm_max_retries",
    "NEWS_HOURS": "advanced.rss_hours",
    "RSS_MAX_CONCURRENT": "advanced.rss_max_concurrent",
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    深度合并两个字典

    Args:
        base: 基础字典
        override: 覆盖字典

    Returns:
        合并后的字典
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _set_nested_value(
    data: dict[str, Any], path: str, value: Any, only_if_empty: bool = True
) -> None:
    """
    设置嵌套字典的值

    Args:
        data: 目标字典
        path: 点分隔的路径，如 "llm.api_key"
        value: 要设置的值
        only_if_empty: 仅当当前值为空时才设置
    """
    keys = path.split(".")
    current = data

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    final_key = keys[-1]
    if only_if_empty:
        # 只在当前值为空（空字符串、None、空列表）时才覆盖
        current_value = current.get(final_key)
        if not current_value:
            current[final_key] = value
    else:
        current[final_key] = value


def _parse_categories(value: str) -> list[str]:
    """
    解析 CATEGORIES 环境变量

    处理以下格式:
    - "cs.AI,cs.CL,cs.CV" → ["cs.AI", "cs.CL", "cs.CV"]
    - "cs.AI, cs.CL, cs.CV" → ["cs.AI", "cs.CL", "cs.CV"]  # 带空格
    - " cs.AI , cs.CL " → ["cs.AI", "cs.CL"]  # 首尾空格
    """
    return [cat.strip() for cat in value.split(",") if cat.strip()]


def _convert_env_value(path: str, value: str) -> Any:
    """
    根据配置路径转换环境变量值的类型

    Args:
        path: 配置路径
        value: 环境变量值（字符串）

    Returns:
        转换后的值
    """
    # 列表类型
    if path == "arxiv.categories":
        return _parse_categories(value)

    # 整数类型
    int_paths = {
        "arxiv.max_results",
        "arxiv.max_pages",
        "search.max_results",
        "search.timeout",
        "analysis.max_concurrent",
        "analysis.timeout",
        "analysis.max_research_iterations",
        "analysis.max_write_iterations",
        "notification.max_papers",
        "notification.max_news",
        "notification.timeout",
        "notification.max_retries",
        "advanced.llm_timeout",
        "advanced.llm_max_retries",
        "advanced.rss_hours",
        "advanced.rss_max_concurrent",
    }
    if path in int_paths:
        return int(value)

    # 浮点数类型
    float_paths = {"arxiv.request_delay"}
    if path in float_paths:
        return float(value)

    # 默认返回字符串
    return value


def _load_yaml_config(config_path: Path) -> dict[str, Any]:
    """
    加载 YAML 配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典，文件不存在或为空时返回空字典
    """
    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)
        return content if content else {}


def _load_env_config() -> dict[str, Any]:
    """
    从环境变量加载配置

    Returns:
        配置字典
    """
    config: dict[str, Any] = {}

    for env_var, config_path in ENV_MAPPING.items():
        value = os.environ.get(env_var)
        if value:
            converted_value = _convert_env_value(config_path, value)
            _set_nested_value(config, config_path, converted_value, only_if_empty=False)

    return config


def _find_config_file() -> Path:
    """
    查找配置文件路径

    查找顺序：
    1. 项目根目录下的 config/settings.yaml
    2. 当前工作目录下的 config/settings.yaml

    Returns:
        配置文件路径（可能不存在）
    """
    # 尝试从当前文件位置向上查找项目根目录
    current = Path(__file__).resolve()
    for parent in current.parents:
        config_path = parent / "config" / "settings.yaml"
        if config_path.exists():
            return config_path
        # 如果找到 src 目录的父目录，就认为是项目根目录
        if (parent / "src").is_dir():
            return parent / "config" / "settings.yaml"

    # 回退到当前工作目录
    return Path.cwd() / "config" / "settings.yaml"


def load_settings(
    config_path: Optional[Path] = None, validate: bool = True
) -> Settings:
    """
    加载配置

    按优先级合并配置：YAML 文件 > 环境变量 > 默认值

    Args:
        config_path: 配置文件路径，默认自动查找
        validate: 是否验证必填项，默认 True

    Returns:
        Settings 实例

    Raises:
        ValueError: 当 validate=True 且必填配置缺失时
    """
    # 1. 初始化默认配置
    default_config = Settings().model_dump()

    # 2. 加载 YAML 配置
    if config_path is None:
        config_path = _find_config_file()
    yaml_config = _load_yaml_config(config_path)

    # 3. 加载环境变量配置
    env_config = _load_env_config()

    # 4. 按优先级合并：默认值 < 环境变量 < YAML 文件
    merged = _deep_merge(default_config, env_config)
    merged = _deep_merge(merged, yaml_config)

    # 5. 创建 Settings 实例
    settings = Settings.model_validate(merged)

    # 6. 验证必填项
    if validate:
        settings.validate_required()

    return settings


def load_settings_without_validation(config_path: Optional[Path] = None) -> Settings:
    """
    加载配置但不验证必填项

    用于配置检查等场景，允许配置不完整。

    Args:
        config_path: 配置文件路径，默认自动查找

    Returns:
        Settings 实例（可能不完整）
    """
    return load_settings(config_path=config_path, validate=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    获取全局配置单例

    使用 @lru_cache 缓存，全局只加载一次。
    首次调用时自动验证配置。

    Returns:
        Settings 实例

    Raises:
        ValueError: 当必填配置缺失时
    """
    return load_settings()


def reload_settings() -> Settings:
    """
    清除缓存并重新加载配置

    Returns:
        新的 Settings 实例
    """
    get_settings.cache_clear()
    return get_settings()
