"""
论文内容查询工具

允许 Researcher Agent 查询论文的特定章节或搜索特定内容。
"""

import logging
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.data_fetchers.pdf.models import ParsedPaper, SectionType

logger = logging.getLogger(__name__)

# 全局存储当前论文（在深度分析开始时设置）
_current_paper: Optional[ParsedPaper] = None


def set_current_paper(paper: Optional[ParsedPaper]) -> None:
    """设置当前分析的论文"""
    global _current_paper
    _current_paper = paper


def get_current_paper() -> Optional[ParsedPaper]:
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


def _parse_section_type(section_name: str) -> SectionType:
    """解析章节类型字符串"""
    mapping = {
        "abstract": SectionType.ABSTRACT,
        "introduction": SectionType.INTRODUCTION,
        "intro": SectionType.INTRODUCTION,
        "related": SectionType.RELATED_WORK,
        "related_work": SectionType.RELATED_WORK,
        "background": SectionType.RELATED_WORK,
        "method": SectionType.METHOD,
        "methods": SectionType.METHOD,
        "methodology": SectionType.METHOD,
        "approach": SectionType.METHOD,
        "experiment": SectionType.EXPERIMENT,
        "experiments": SectionType.EXPERIMENT,
        "evaluation": SectionType.EXPERIMENT,
        "results": SectionType.RESULTS,
        "result": SectionType.RESULTS,
        "findings": SectionType.RESULTS,
        "discussion": SectionType.DISCUSSION,
        "analysis": SectionType.DISCUSSION,
        "conclusion": SectionType.CONCLUSION,
        "conclusions": SectionType.CONCLUSION,
        "summary": SectionType.CONCLUSION,
    }
    return mapping.get(section_name.lower().strip(), SectionType.OTHER)


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

        if paper.parse_status != "success":
            return f"论文 PDF 解析失败: {paper.parse_error or '未知错误'}"

        results: list[str] = []

        # 按章节查询
        if section:
            section_type = _parse_section_type(section)
            found = False
            for sec in paper.sections:
                if sec.section_type == section_type:
                    found = True
                    content = sec.content[:4000]  # 限制长度
                    results.append(f"## {sec.title}\n\n{content}")
                    if len(sec.content) > 4000:
                        results.append(
                            "\n... (内容已截断，如需更多请指定关键词搜索)"
                        )
            if not found:
                results.append(f"未找到 '{section}' 章节。可用章节: {', '.join(s.title for s in paper.sections)}")

        # 按关键词搜索
        if keyword:
            keyword_results: list[str] = []
            keyword_lower = keyword.lower()
            for sec in paper.sections:
                if keyword_lower in sec.content.lower():
                    # 提取包含关键词的上下文
                    context = _extract_keyword_context(sec.content, keyword)
                    if context:
                        keyword_results.append(
                            f"### 在 {sec.title} 中找到:\n{context}"
                        )

            if keyword_results:
                results.extend(keyword_results[:5])  # 最多 5 个匹配
            else:
                results.append(f"未在论文中找到关键词 '{keyword}'")

        # 包含表格
        if include_tables and paper.tables:
            table_texts: list[str] = []
            for table in paper.tables[:3]:  # 最多 3 个表格
                header = f"### {table.table_id}"
                if table.caption:
                    header += f": {table.caption}"
                table_texts.append(f"{header}\n\n{table.raw_text[:1000]}")
            if table_texts:
                results.append("\n## 表格内容\n\n" + "\n\n".join(table_texts))

        # 包含图表说明
        if include_figures and paper.figures:
            figure_texts: list[str] = []
            for fig in paper.figures[:10]:  # 最多 10 个图表
                figure_texts.append(
                    f"- **{fig.figure_id}** (Page {fig.page}): {fig.caption}"
                )
            if figure_texts:
                results.append("\n## 图表说明\n\n" + "\n".join(figure_texts))

        if not results:
            # 没有指定任何查询参数，返回概览
            overview_parts = [
                f"论文: {paper.title}",
                f"总页数: {paper.total_pages}",
                f"章节数: {len(paper.sections)}",
                f"表格数: {len(paper.tables)}",
                f"图表数: {len(paper.figures)}",
                f"参考文献数: {len(paper.references)}",
                "",
                "可用章节:",
            ]
            for sec in paper.sections:
                overview_parts.append(f"  - {sec.title} ({sec.token_count} tokens)")

            return "\n".join(overview_parts) + "\n\n请指定 section 或 keyword 参数查询具体内容。"

        return "\n\n".join(results)

    return paper_reader

