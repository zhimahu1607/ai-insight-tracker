"""
论文分析模块

提供论文浅度分析和深度分析功能。

浅度分析:
    使用单次 LLM 调用对论文摘要进行快速的结构化摘要生成。

深度分析:
    使用 LangGraph Multi-Agent 系统对指定论文进行深入研究分析。

Usage:
    from src.agents.paper import PaperLightAnalyzer, run_deep_analysis

    # 浅度分析
    analyzer = PaperLightAnalyzer(llm_client)
    analyzed_papers = await analyzer.analyze_batch(papers)

    # 深度分析
    result = await run_deep_analysis(
        paper_id="2501.12345",
        paper_title="...",
        paper_abstract="...",
        paper_pdf_url="...",
    )
"""

from .light_analyzer import PaperLightAnalyzer
from .deep_analyzer import run_deep_analysis, DeepAnalysisResult

__all__ = [
    # 浅度分析
    "PaperLightAnalyzer",
    # 深度分析
    "run_deep_analysis",
    "DeepAnalysisResult",
]
