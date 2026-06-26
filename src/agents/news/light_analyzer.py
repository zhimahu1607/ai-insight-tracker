"""News light analyzer."""

from src.agents.base_analyzer import BaseLightAnalyzer
from src.models import AnalyzedNews, NewsItem, NewsLightAnalysis


class NewsLightAnalyzer(BaseLightAnalyzer[NewsItem, AnalyzedNews, NewsLightAnalysis]):
    """Run structured light analysis for news items."""

    def _get_prompt_key(self) -> str:
        return "news"

    def _build_user_content(self, item: NewsItem) -> str:
        content = item.content or item.summary or "No content"
        return self._user_prompt.format(
            title=item.title,
            source_name=item.source_name,
            content=content,
        )

    def _create_output(self, item: NewsItem) -> AnalyzedNews:
        return AnalyzedNews(
            **item.model_dump(),
            analysis_status="pending",
        )

    def _get_analysis_schema(self) -> type[NewsLightAnalysis]:
        return NewsLightAnalysis

    def _set_analysis_result(
        self,
        output: AnalyzedNews,
        analysis: NewsLightAnalysis,
    ) -> None:
        output.light_analysis = analysis

    def _get_item_id(self, item: NewsItem) -> str:
        return item.id

    def _get_progress_desc(self) -> str:
        return "news analysis"

    def _get_progress_unit(self) -> str:
        return "item"
