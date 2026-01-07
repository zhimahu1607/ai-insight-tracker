"""
RSS 解析器（内部模块）

使用 feedparser 解析 RSS/Atom 格式的 XML 内容。
作为 NewsFetcher 的内部组件。
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import feedparser
from dateutil import parser as date_parser

from src.models import RSSSource, NewsItem

logger = logging.getLogger(__name__)


def parse_feed_sync(content: str, source: RSSSource) -> list[NewsItem]:
    """
    同步解析 RSS Feed 内容

    此函数是同步的，设计为在线程池中执行，避免阻塞事件循环。

    Args:
        content: RSS XML 内容
        source: RSS 源配置

    Returns:
        NewsItem 列表
    """
    feed = feedparser.parse(content)
    items: list[NewsItem] = []

    for entry in feed.entries:
        try:
            item = _entry_to_news_item(entry, source)
            items.append(item)
        except Exception as e:
            logger.warning(f"解析 RSS 条目失败 ({source.name}): {e}")
            continue

    return items


def _entry_to_news_item(entry: Any, source: RSSSource) -> NewsItem:
    """
    将 feedparser entry 转换为 NewsItem 对象

    Args:
        entry: feedparser entry 对象
        source: RSS 源配置

    Returns:
        NewsItem 对象
    """
    # 获取 URL（优先使用 link，其次使用 id）
    url = entry.get("link") or entry.get("id", "")
    if not url:
        raise ValueError("RSS 条目缺少 URL")

    # 生成唯一 ID（基于 URL 的 MD5 hash）
    item_id = generate_id(url)

    # 获取标题
    title = entry.get("title", "").strip()
    if not title:
        raise ValueError("RSS 条目缺少标题")

    # 解析发布时间
    published = _parse_date(entry)

    # 获取摘要
    summary = _extract_summary(entry)

    return NewsItem(
        id=item_id,
        title=title,
        url=url,
        source_name=source.name,
        source_category=source.category,
        language=source.language,
        published=published,
        summary=summary,
        weight=source.weight,
    )


def generate_id(url: str) -> str:
    """
    基于 URL 生成唯一 ID

    使用 MD5 hash 的前 16 位作为 ID。

    Args:
        url: 原文 URL

    Returns:
        16 位十六进制 ID
    """
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:16]


def _parse_date(entry: Any) -> datetime:
    """
    解析 RSS 条目的发布时间

    依次尝试解析 published, updated, created 字段，
    失败时使用当前时间。

    Args:
        entry: feedparser entry 对象

    Returns:
        datetime 对象（带时区）
    """
    # 尝试的字段顺序
    date_fields = ["published", "updated", "created"]

    for field in date_fields:
        date_str = entry.get(field)
        if date_str:
            try:
                dt = date_parser.parse(date_str)
                # 确保有时区信息
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, TypeError):
                continue

    # 尝试使用 feedparser 的 struct_time
    for field in date_fields:
        parsed_field = f"{field}_parsed"
        time_tuple = entry.get(parsed_field)
        if time_tuple:
            try:
                from time import mktime
                timestamp = mktime(time_tuple)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except (ValueError, TypeError, OverflowError):
                continue

    # 所有尝试都失败，返回当前时间
    logger.warning(f"无法解析日期，使用当前时间: {entry.get('title', 'unknown')}")
    return datetime.now(timezone.utc)


def _extract_summary(entry: Any) -> Optional[str]:
    """
    提取 RSS 条目的摘要

    优先使用 summary 字段，其次使用 description。

    Args:
        entry: feedparser entry 对象

    Returns:
        摘要文本或 None
    """
    # 尝试获取摘要
    summary = entry.get("summary") or entry.get("description")

    if not summary:
        return None

    # 清理 HTML 标签（简单处理）
    import re
    clean_summary = re.sub(r"<[^>]+>", "", summary)
    clean_summary = clean_summary.strip()

    # 限制长度
    max_length = 500
    if len(clean_summary) > max_length:
        clean_summary = clean_summary[:max_length] + "..."

    return clean_summary if clean_summary else None

