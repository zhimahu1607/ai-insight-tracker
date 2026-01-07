"""
Web 爬虫模块

基于 crawl4ai 实现异步网页爬取，用于获取无 RSS 源的公司博客。
"""

from .client import AsyncNewsCrawler
from .base import BaseExtractor

__all__ = [
    "AsyncNewsCrawler",
    "BaseExtractor",
]

