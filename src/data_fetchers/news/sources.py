"""
新闻源配置加载

从 YAML 配置文件加载新闻源列表。
"""

import logging
from pathlib import Path
from typing import Optional, Union

import yaml

from src.models import NewsSource

logger = logging.getLogger(__name__)

# 默认配置文件路径
DEFAULT_NEWS_CONFIG_PATH = Path("config/news_sources.yaml")


def load_news_sources(
    config_path: Optional[Union[str, Path]] = None
) -> list[NewsSource]:
    """
    从 YAML 配置文件加载新闻源列表

    Args:
        config_path: 配置文件路径，None 时使用默认路径

    Returns:
        NewsSource 列表

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML 解析错误
    """
    if config_path is None:
        config_path = DEFAULT_NEWS_CONFIG_PATH
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"新闻源配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not config or "sources" not in config:
        logger.warning("新闻源配置文件为空或格式错误")
        return []

    sources: list[NewsSource] = []
    for item in config["sources"]:
        try:
            source = NewsSource(**item)
            sources.append(source)
        except Exception as e:
            logger.warning(
                f"解析新闻源失败: {item.get('name', 'unknown')} - {e}"
            )
            continue

    # 统计
    enabled_count = sum(1 for s in sources if s.enabled)
    rss_count = sum(1 for s in sources if s.enabled and s.fetch_type.value == "rss")
    crawler_count = sum(1 for s in sources if s.enabled and s.fetch_type.value == "crawler")

    logger.info(
        f"加载新闻源: 共 {len(sources)} 个, "
        f"启用 {enabled_count} 个 "
        f"(RSS: {rss_count}, Crawler: {crawler_count})"
    )

    return sources

