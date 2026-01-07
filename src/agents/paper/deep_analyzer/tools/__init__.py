"""
深度分析工具模块

提供 Researcher Agent 使用的异步工具。
"""

from .search import search_web, get_search_tool
from .arxiv_loader import load_arxiv
from .paper_reader import (
    get_paper_reader_tool,
    set_current_paper,
    get_current_paper,
    clear_current_paper,
)

__all__ = [
    "search_web",
    "get_search_tool",
    "load_arxiv",
    # 论文全文查询
    "get_paper_reader_tool",
    "set_current_paper",
    "get_current_paper",
    "clear_current_paper",
]
