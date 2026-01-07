"""
论文深度分析模块

使用 LangGraph 实现 Multi-Agent 系统，对指定论文进行深入研究分析。
支持论文全文分析（通过 PDF 下载和解析）。

Architecture:
    [PDF 预处理] → Supervisor → Researcher ↔ Supervisor → Writer → Reviewer → [Writer | END]

Usage:
    from src.agents.paper.deep_analyzer import run_deep_analysis, DeepAnalysisResult

    result = await run_deep_analysis(
        paper_id="2501.12345",
        paper_title="...",
        paper_abstract="...",
        paper_pdf_url="...",
        requirements="请重点分析方法创新点",
        enable_full_text=True,  # 启用全文分析
    )
    print(result.report)
"""

import logging
from datetime import datetime, timezone
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

    # 全文分析信息 (新增)
    full_text_enabled: bool = Field(default=False, description="是否启用了全文分析")
    pdf_parse_status: str = Field(default="pending", description="PDF 解析状态")
    paper_total_pages: int = Field(default=0, description="论文总页数")


async def run_deep_analysis(
    paper_id: str,
    paper_title: str,
    paper_abstract: str,
    paper_pdf_url: str,
    requirements: Optional[str] = None,
    enable_full_text: bool = True,
) -> DeepAnalysisResult:
    """
    执行深度分析

    Args:
        paper_id: arXiv 论文 ID
        paper_title: 论文标题
        paper_abstract: 论文摘要
        paper_pdf_url: PDF 下载链接
        requirements: 用户指定的分析需求（可选）
        enable_full_text: 是否启用全文分析（下载并解析 PDF）

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

    # === PDF 预处理阶段 (新增) ===
    paper_full_content: Optional[str] = None
    paper_tables_content: Optional[str] = None
    paper_figures_content: Optional[str] = None
    paper_sections_available = False
    paper_total_pages = 0
    paper_references_count = 0
    pdf_parse_status = "pending"

    if enable_full_text:
        logger.info(f"开始下载和解析 PDF: {paper_id}")
        try:
            from src.data_fetchers.pdf import load_paper_pdf, PaperChunker

            # 下载并解析 PDF
            parsed_paper = await load_paper_pdf(
                paper_id=paper_id,
                paper_title=paper_title,
                pdf_url=paper_pdf_url,
                download_timeout=settings.pdf.download_timeout if hasattr(settings, 'pdf') else 120.0,
            )

            if parsed_paper.parse_status == "success":
                # 设置全局论文内容（供 paper_reader 工具使用）
                set_current_paper(parsed_paper)

                # 获取概要上下文
                chunker = PaperChunker(
                    max_tokens_per_chunk=settings.pdf.max_tokens_per_chunk if hasattr(settings, 'pdf') else 4000,
                )
                paper_full_content = chunker.get_summary_context(parsed_paper)
                paper_tables_content = chunker.get_tables_context(parsed_paper)
                paper_figures_content = chunker.get_figures_context(parsed_paper)
                paper_sections_available = len(parsed_paper.sections) > 0
                paper_total_pages = parsed_paper.total_pages
                paper_references_count = len(parsed_paper.references)
                pdf_parse_status = "success"

                logger.info(
                    f"PDF 解析成功: {paper_id}, "
                    f"页数={paper_total_pages}, 章节={len(parsed_paper.sections)}, "
                    f"表格={len(parsed_paper.tables)}, 图表={len(parsed_paper.figures)}"
                )
            else:
                pdf_parse_status = "failed"
                logger.warning(f"PDF 解析失败: {parsed_paper.parse_error}")

        except Exception as e:
            pdf_parse_status = "failed"
            logger.warning(f"PDF 处理失败，将使用摘要进行分析: {e}")
    else:
        pdf_parse_status = "disabled"
        logger.info("全文分析已禁用，仅使用摘要进行分析")

    # 创建初始状态
    initial_state = create_initial_state(
        paper_id=paper_id,
        paper_title=paper_title,
        paper_abstract=paper_abstract,
        paper_pdf_url=paper_pdf_url,
        requirements=requirements,
        max_iterations=max_iterations,
        max_write_iterations=max_write_iterations,
        # 论文全文相关参数
        paper_full_content=paper_full_content,
        paper_tables_content=paper_tables_content,
        paper_figures_content=paper_figures_content,
        paper_sections_available=paper_sections_available,
        paper_total_pages=paper_total_pages,
        paper_references_count=paper_references_count,
        pdf_parse_status=pdf_parse_status,
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
    finally:
        # 清理全局论文内容
        clear_current_paper()

    # 计算耗时
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # 提取结果
    final_report = final_state.get("final_report") or final_state.get("draft_report", "")
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
        full_text_enabled=enable_full_text,
        pdf_parse_status=pdf_parse_status,
        paper_total_pages=paper_total_pages,
    )

    logger.info(
        f"深度分析完成: {paper_id}, "
        f"研究迭代: {result.research_iterations}, "
        f"写作迭代: {result.write_iterations}, "
        f"全文分析: {pdf_parse_status}, "
        f"耗时: {duration:.1f}s"
    )

    return result


__all__ = [
    "run_deep_analysis",
    "DeepAnalysisResult",
]
