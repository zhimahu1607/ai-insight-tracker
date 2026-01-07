"""
日报数据模型

定义每日统计信息和完整日报结构。
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .paper import AnalyzedPaper
from .news import AnalyzedNews


class DailyStats(BaseModel):
    """每日统计信息"""

    total_papers: int = Field(description="论文总数")
    papers_by_category: dict[str, int] = Field(
        default_factory=dict, description="按分类统计论文数"
    )
    total_news: int = Field(description="热点总数")
    news_by_category: dict[str, int] = Field(
        default_factory=dict, description="按分类统计热点数"
    )
    top_keywords: list[str] = Field(default_factory=list, description="热门关键词")


class DailyReport(BaseModel):
    """每日报告模型"""

    date: str = Field(description="日期 YYYY-MM-DD")
    summary: str = Field(description="AI 生成的当日总结")
    category_summaries: dict[str, str] = Field(
        default_factory=dict, description="按领域分类的总结"
    )
    news_summary: str = Field(default="", description="热点新闻总结")
    stats: DailyStats = Field(description="统计信息")
    generated_at: datetime = Field(description="生成时间")

    # === 便捷属性 (计算属性，不序列化) ===
    @property
    def paper_count(self) -> int:
        """论文总数"""
        return self.stats.total_papers

    @property
    def news_count(self) -> int:
        """热点总数"""
        return self.stats.total_news

    def get_highlight_papers(self, count: int = 10) -> list[AnalyzedPaper]:
        """
        获取精选论文 (已弃用: 数据不再存储于 Report 中)
        """
        return []

    def get_highlight_news(self, count: int = 5) -> list[AnalyzedNews]:
        """
        获取精选热点 (已弃用: 数据不再存储于 Report 中)
        """
        return []

    def get_successful_papers(self) -> list[AnalyzedPaper]:
        """获取分析成功的论文列表 (已弃用)"""
        return []

    def get_successful_news(self) -> list[AnalyzedNews]:
        """获取分析成功的热点列表 (已弃用)"""
        return []

    @property
    def analysis_success_rate(self) -> dict[str, float]:
        """获取分析成功率 (依赖外部统计，此处仅返回默认值)"""
        return {"papers": 1.0, "news": 1.0}

