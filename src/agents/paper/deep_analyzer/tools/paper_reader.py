"""
论文内容查询工具

允许 Researcher Agent 查询论文的特定章节或搜索特定内容。
"""

import logging
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.models.arxiv_html_fulltext import ArxivHtmlFulltext, ArxivHtmlSection

logger = logging.getLogger(__name__)

# 全局存储当前论文（在深度分析开始时设置）
_current_paper: Optional[ArxivHtmlFulltext] = None


def set_current_paper(paper: Optional[ArxivHtmlFulltext]) -> None:
    """设置当前分析的论文"""
    global _current_paper
    _current_paper = paper


def get_current_paper() -> Optional[ArxivHtmlFulltext]:
    """获取当前分析的论文"""
    return _current_paper


def clear_current_paper() -> None:
    """清除当前论文（分析结束后调用）"""
    global _current_paper
    _current_paper = None


class PaperReaderInput(BaseModel):
    """论文内容查询输入"""

    section: Optional[str] = Field(
        default=None,
        description="要查询的章节类型: abstract, introduction, method, experiment, results, conclusion, discussion, related_work",
    )
    keyword: Optional[str] = Field(
        default=None, description="在论文中搜索的关键词"
    )
    include_tables: bool = Field(
        default=False, description="是否包含表格内容"
    )
    include_figures: bool = Field(
        default=False, description="是否包含图表说明"
    )


def _normalize(s: str) -> str:
    return " ".join((s or "").lower().split())


def _walk_sections(sections: list[ArxivHtmlSection]) -> list[ArxivHtmlSection]:
    out: list[ArxivHtmlSection] = []
    stack = list(sections)
    while stack:
        s = stack.pop(0)
        out.append(s)
        if s.children:
            stack[0:0] = s.children
    return out


def _match_section_by_key(
    sections: list[ArxivHtmlSection], key: str
) -> list[ArxivHtmlSection]:
    """
    将用户 section key 映射到可能的章节标题关键词（粗匹配）
    """
    key = _normalize(key)
    candidates: list[str]
    mapping: dict[str, list[str]] = {
        "abstract": ["abstract"],
        "introduction": ["introduction", "intro"],
        "intro": ["introduction", "intro"],
        "related": ["related", "background", "prior work"],
        "related_work": ["related", "background", "prior work"],
        "method": ["method", "methods", "methodology", "approach"],
        "experiment": ["experiment", "experiments", "evaluation", "setup"],
        "results": ["results", "result", "findings"],
        "discussion": ["discussion", "analysis"],
        "conclusion": ["conclusion", "conclusions", "summary"],
    }
    candidates = mapping.get(key, [key])

    matched: list[ArxivHtmlSection] = []
    for s in _walk_sections(sections):
        title = _normalize(s.title)
        heading = _normalize(s.heading)
        if any(c in title for c in candidates) or any(c in heading for c in candidates):
            matched.append(s)
    return matched


def _extract_keyword_context(text: str, keyword: str, context_chars: int = 500) -> str:
    """提取关键词上下文"""
    keyword_lower = keyword.lower()
    text_lower = text.lower()

    contexts: list[str] = []
    start = 0

    while True:
        pos = text_lower.find(keyword_lower, start)
        if pos == -1:
            break

        # 提取上下文
        ctx_start = max(0, pos - context_chars // 2)
        ctx_end = min(len(text), pos + len(keyword) + context_chars // 2)

        context = text[ctx_start:ctx_end]
        if ctx_start > 0:
            context = "..." + context
        if ctx_end < len(text):
            context = context + "..."

        contexts.append(context)
        start = pos + len(keyword)

        # 最多返回 3 个匹配
        if len(contexts) >= 3:
            break

    return "\n\n---\n\n".join(contexts)


def get_paper_reader_tool():
    """
    获取论文内容查询工具
    """

    @tool(args_schema=PaperReaderInput)
    async def paper_reader(
        section: Optional[str] = None,
        keyword: Optional[str] = None,
        include_tables: bool = False,
        include_figures: bool = False,
    ) -> str:
        """
        查询当前论文的全文内容。

        使用场景：
        - 查看论文的特定章节（如 method, experiment, results）
        - 搜索论文中提到的特定技术或概念
        - 获取实验设置和结果的详细信息
        - 查看论文中的表格数据

        Args:
            section: 章节名称（如 introduction, method, experiment, results, conclusion）
            keyword: 搜索关键词
            include_tables: 是否包含表格内容
            include_figures: 是否包含图表说明

        Returns:
            相关的论文内容
        """
        paper = get_current_paper()
        if paper is None:
            return "论文全文内容尚未加载。请使用其他工具获取论文信息。"

        results: list[str] = []

        # 按章节查询
        if section:
            matched = _match_section_by_key(paper.sections, section)
            if not matched:
                all_titles = [s.heading for s in _walk_sections(paper.sections)]
                results.append(
                    f"未找到 '{section}' 章节。可用章节: {', '.join(all_titles[:30])}"
                )
            else:
                for sec in matched[:3]:
                    content = "\n\n".join(sec.paragraphs)
                    content = content[:4000]
                    results.append(f"## {sec.heading}\n\n{content}")
                    if len("\n\n".join(sec.paragraphs)) > 4000:
                        results.append("\n... (内容已截断，如需更多请指定关键词搜索)")

        # 按关键词搜索
        if keyword:
            keyword_results: list[str] = []
            keyword_lower = keyword.lower()
            for sec in _walk_sections(paper.sections):
                joined = "\n\n".join(sec.paragraphs)
                if keyword_lower in joined.lower():
                    context = _extract_keyword_context(joined, keyword)
                    if context:
                        keyword_results.append(f"### 在 {sec.heading} 中找到:\n{context}")

            if keyword_results:
                results.extend(keyword_results[:5])  # 最多 5 个匹配
            else:
                results.append(f"未在论文中找到关键词 '{keyword}'")

        # 包含表格
        if include_tables:
            results.append("HTML 版本暂不支持表格结构化提取（已忽略 include_tables）。")

        # 包含图表说明
        if include_figures:
            results.append("HTML 版本暂不支持图表说明结构化提取（已忽略 include_figures）。")

        if not results:
            # 没有指定任何查询参数，返回概览
            overview_parts = [
                f"论文: {paper.title}",
                f"章节数: {len(_walk_sections(paper.sections))}",
                "",
                "可用章节:",
            ]
            for sec in _walk_sections(paper.sections)[:60]:
                overview_parts.append(f"  - {sec.heading}")

            return "\n".join(overview_parts) + "\n\n请指定 section 或 keyword 参数查询具体内容。"

        return "\n\n".join(results)

    return paper_reader

