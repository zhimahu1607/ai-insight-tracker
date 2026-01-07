"""
分析模块 (Agents Package)

提供论文分析和热点分析功能。

Modules:
    paper: 论文分析模块（浅度分析 + 深度分析）
    news: 热点分析模块（浅度分析）
    shared: 全局共享资源（LLM 并发控制信号量）

Usage:
    from src.agents.paper import PaperLightAnalyzer, run_deep_analysis
    from src.agents.news import NewsLightAnalyzer
    from src.agents.shared import get_llm_semaphore

    # 论文浅度分析
    paper_analyzer = PaperLightAnalyzer(llm_client)
    analyzed_papers = await paper_analyzer.analyze_batch(papers)

    # 论文深度分析
    result = await run_deep_analysis(
        paper_id="2501.12345",
        paper_title="...",
        paper_abstract="...",
        paper_pdf_url="...",
    )

    # 热点分析
    news_analyzer = NewsLightAnalyzer(llm_client)
    analyzed_news = await news_analyzer.analyze_batch(news_items)
"""

from .shared import get_llm_semaphore, reset_llm_semaphore
from .base_analyzer import BaseLightAnalyzer
from .paper import PaperLightAnalyzer, run_deep_analysis, DeepAnalysisResult
from .news import NewsLightAnalyzer

__all__ = [
    # 共享资源
    "get_llm_semaphore",
    "reset_llm_semaphore",
    # 基类
    "BaseLightAnalyzer",
    # 论文分析
    "PaperLightAnalyzer",
    "run_deep_analysis",
    "DeepAnalysisResult",
    # 热点分析
    "NewsLightAnalyzer",
]
