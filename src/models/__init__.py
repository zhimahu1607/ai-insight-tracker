"""
数据模型

使用 Pydantic v2 定义项目中所有核心数据模型，提供类型安全和数据验证。
"""

from .common import Tags, Keywords
from .paper import (
    CodeRepositorySignal,
    OpenAlexSignal,
    OpenReviewSignal,
    Paper,
    PaperExternalIds,
    PaperLightAnalysis,
    PaperQualitySignals,
    PapersWithCodeSignal,
    SemanticScholarSignal,
    AnalyzedPaper,
)
from .news import (
    FetchType,
    RSSSource,
    NewsSource,
    NewsItem,
    NewsLightAnalysis,
    AnalyzedNews,
)
from .daily_report import DailyStats, DailyReport

__all__ = [
    # 共享类型
    "Tags",
    "Keywords",
    # 论文模型
    "CodeRepositorySignal",
    "OpenAlexSignal",
    "OpenReviewSignal",
    "Paper",
    "PaperExternalIds",
    "PaperLightAnalysis",
    "PaperQualitySignals",
    "PapersWithCodeSignal",
    "SemanticScholarSignal",
    "AnalyzedPaper",
    # 热点模型
    "FetchType",
    "RSSSource",
    "NewsSource",
    "NewsItem",
    "NewsLightAnalysis",
    "AnalyzedNews",
    # 日报模型
    "DailyStats",
    "DailyReport",
]
