"""
论文深度分析模块

使用 LangGraph 实现 Multi-Agent 系统，对指定论文进行深入研究分析。
支持论文全文分析（通过 arXiv 官方 HTML 获取和解析）。

Architecture:
    [arXiv HTML 全文预处理] → Supervisor → Researcher ↔ Supervisor → Writer → Reviewer → [Writer | END]

Usage:
    from src.agents.paper.deep_analyzer import run_deep_analysis, DeepAnalysisResult

    result = await run_deep_analysis(
        paper_id="2501.12345",
        paper_title="...",
        paper_abstract="...",
        requirements="请重点分析方法创新点",
    )
    print(result.report)
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from src.config import get_settings
from .state import DeepAnalysisState, create_initial_state
from .graph import get_compiled_graph
from .tools import set_current_paper, clear_current_paper


logger = logging.getLogger(__name__)


class DeepAnalysisResult(BaseModel):
    """深度分析结果"""

    paper_id: str = Field(description="论文 ID")
    paper_title: str = Field(description="论文标题")

    # 完整报告
    report: str = Field(description="Markdown 格式的完整分析报告")

    # 研究过程记录
    research_notes: list[str] = Field(
        default_factory=list, description="研究过程中的笔记"
    )
    research_iterations: int = Field(default=0, description="研究迭代次数")
    write_iterations: int = Field(default=0, description="写作修改次数")

    # 元信息
    analyzed_at: datetime = Field(description="分析完成时间")
    analysis_duration_seconds: float = Field(
        default=0.0, description="分析耗时（秒）"
    )
    llm_provider: str = Field(default="", description="使用的 LLM 提供商")
    llm_model: str = Field(default="", description="使用的 LLM 模型")

    # 全文分析信息
    fulltext_parse_status: str = Field(default="pending", description="全文解析状态")
    paper_total_sections: int = Field(default=0, description="论文章节总数（含子章节）")
    paper_html_url: str = Field(default="", description="arXiv 官方 HTML 全文链接")


async def run_deep_analysis(
    paper_id: str,
    paper_title: str,
    paper_abstract: str,
    requirements: Optional[str] = None,
    ) -> DeepAnalysisResult:
    """
    执行深度分析

    Args:
        paper_id: arXiv 论文 ID
        paper_title: 论文标题
        paper_abstract: 论文摘要
        requirements: 用户指定的分析需求（可选）

    Returns:
        DeepAnalysisResult: 分析结果

    Raises:
        Exception: 分析过程中的异常
    """
    logger.info(f"开始深度分析: {paper_id} - {paper_title[:50]}...")

    # 获取配置
    settings = get_settings()
    max_iterations = settings.analysis.max_research_iterations
    max_write_iterations = settings.analysis.max_write_iterations

    # 记录开始时间
    start_time = datetime.now(timezone.utc)

    # === arXiv HTML 全文预处理阶段 ===
    paper_full_content: Optional[str] = None
    paper_tables_content: Optional[str] = None
    paper_figures_content: Optional[str] = None
    paper_sections_available = False
    paper_total_sections = 0
    paper_references_count = 0
    fulltext_parse_status = "pending"
    paper_html_url = ""

    # 获取论文全文（严格使用官方 arXiv HTML）
    logger.info(f"开始获取和解析 arXiv HTML 全文: {paper_id}")
    from src.data_fetchers.arxiv.html_fulltext import (
        build_fulltext_summary_context,
        count_sections,
        fetch_arxiv_html_fulltext,
    )

    fulltext = await fetch_arxiv_html_fulltext(paper_id=paper_id)

    # 保存结构化全文（用于调试/复用）
    try:
        project_root = Path(__file__).resolve().parents[4]  # ai-insight-tracker/
        data_dir = project_root / "data"
        out_path = data_dir / f"arxiv_html_fulltext_{paper_id}.json"
        out_path.write_text(fulltext.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"保存 arXiv HTML 全文结构化结果失败（不影响分析继续）: {e}")

    # 设置全局论文内容（供 paper_reader 工具使用）
    set_current_paper(fulltext)
    try:
        fulltext_parse_status = "success"
        paper_html_url = str(fulltext.source.url)

        # 生成给 Writer 的“全文概要上下文”
        paper_full_content = build_fulltext_summary_context(fulltext)
        paper_tables_content = None
        paper_figures_content = None
        paper_sections_available = len(fulltext.sections) > 0
        paper_total_sections = count_sections(fulltext.sections)
        paper_references_count = 0  # 官方 HTML 暂不做引用结构化统计

        logger.info(
            f"arXiv HTML 解析成功: {paper_id}, "
            f"章节总数={paper_total_sections}, "
            f"html_chars={fulltext.stats.html_chars}, blocks={fulltext.stats.blocks}"
        )

        # 创建初始状态
        initial_state = create_initial_state(
            paper_id=paper_id,
            paper_title=paper_title,
            paper_abstract=paper_abstract,
            paper_html_url=paper_html_url,
            requirements=requirements,
            max_iterations=max_iterations,
            max_write_iterations=max_write_iterations,
            # 论文全文相关参数
            paper_full_content=paper_full_content,
            paper_tables_content=paper_tables_content,
            paper_figures_content=paper_figures_content,
            paper_sections_available=paper_sections_available,
            paper_total_sections=paper_total_sections,
            paper_references_count=paper_references_count,
            fulltext_parse_status=fulltext_parse_status,
        )
        initial_state["analysis_started_at"] = start_time

        # 获取编译的工作流图
        graph = get_compiled_graph()

        # 异步执行工作流
        try:
            final_state = await graph.ainvoke(initial_state)
        except Exception as e:
            logger.error(f"深度分析执行失败: {e}")
            raise

        # 计算耗时
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        # 提取结果
        final_report = final_state.get("final_report") or final_state.get(
            "draft_report", ""
        )
        if not final_report:
            final_report = "分析未能生成报告"

        # 构建结果
        result = DeepAnalysisResult(
            paper_id=paper_id,
            paper_title=paper_title,
            report=final_report,
            research_notes=final_state.get("research_notes", []),
            research_iterations=final_state.get("research_iterations", 0),
            write_iterations=final_state.get("write_iterations", 0),
            analyzed_at=end_time,
            analysis_duration_seconds=duration,
            llm_provider=settings.llm.provider,
            llm_model=settings.llm.model,
            # 全文分析信息
            fulltext_parse_status=fulltext_parse_status,
            paper_total_sections=paper_total_sections,
            paper_html_url=paper_html_url,
        )

        logger.info(
            f"深度分析完成: {paper_id}, "
            f"研究迭代: {result.research_iterations}, "
            f"写作迭代: {result.write_iterations}, "
            f"全文分析: {fulltext_parse_status}, "
            f"耗时: {duration:.1f}s"
        )

        return result
    finally:
        # 清理全局论文内容
        clear_current_paper()


__all__ = [
    "run_deep_analysis",
    "DeepAnalysisResult",
]
