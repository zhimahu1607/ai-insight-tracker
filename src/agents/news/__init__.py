"""
热点分析模块

提供热点浅度分析功能，对 RSS 采集的科技资讯进行结构化分析。

Usage:
    from src.agents.news import NewsLightAnalyzer

    analyzer = NewsLightAnalyzer(llm_client)
    analyzed_news = await analyzer.analyze_batch(news_items)
"""

from .light_analyzer import NewsLightAnalyzer

__all__ = [
    "NewsLightAnalyzer",
]

