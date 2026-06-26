"""Daily report data models."""

from datetime import datetime

from pydantic import BaseModel, Field


class DailyStats(BaseModel):
    """Aggregated counts for a daily report."""

    total_papers: int = Field(description="Total paper count")
    papers_by_category: dict[str, int] = Field(
        default_factory=dict, description="Paper count by category"
    )
    total_news: int = Field(description="Total news count")
    news_by_category: dict[str, int] = Field(
        default_factory=dict, description="News count by category"
    )
    top_keywords: list[str] = Field(default_factory=list, description="Top keywords")


class DailyReport(BaseModel):
    """Daily report model."""

    date: str = Field(description="Date in YYYY-MM-DD format")
    summary: str = Field(description="LLM-generated daily summary")
    category_summaries: dict[str, str] = Field(
        default_factory=dict, description="Summary by paper category"
    )
    news_summary: str = Field(default="", description="News summary")
    stats: DailyStats = Field(description="Aggregated statistics")
    generated_at: datetime = Field(description="Generation time")

    @property
    def paper_count(self) -> int:
        return self.stats.total_papers

    @property
    def news_count(self) -> int:
        return self.stats.total_news
