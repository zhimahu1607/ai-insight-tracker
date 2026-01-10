"""
文本清洗工具

用于将 RSS/crawler 返回的 HTML 或混合文本规范化为可用于 LLM 分析的纯文本。
"""

from __future__ import annotations

import html as _html
import re
from typing import Optional


_RE_SCRIPT_STYLE = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")
_RE_TAGS = re.compile(r"(?s)<[^>]+>")
_RE_WS = re.compile(r"[ \t\f\v]+")
_RE_NEWLINES = re.compile(r"\n{3,}")


def clean_html_to_text(value: Optional[str]) -> Optional[str]:
    """
    将 HTML/富文本转换为纯文本并做轻量清洗。

    - 去除 script/style
    - 去除 HTML 标签
    - 反转义 HTML entities
    - 规范化空白与换行
    """
    if not value:
        return None

    text = value
    text = _RE_SCRIPT_STYLE.sub("", text)
    text = _RE_TAGS.sub(" ", text)
    text = _html.unescape(text)

    # 规范化空白与换行
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _RE_WS.sub(" ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = _RE_NEWLINES.sub("\n\n", text)
    text = text.strip()

    return text or None


def truncate_text(value: Optional[str], max_length: int) -> Optional[str]:
    if not value:
        return None
    if max_length <= 0:
        return None
    if len(value) <= max_length:
        return value
    return value[:max_length] + "..."


