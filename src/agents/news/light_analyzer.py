"""
热点浅度分析器

继承 BaseLightAnalyzer，实现热点资讯特定的分析逻辑。
"""

from typing import Optional

from src.llm import LLMClient
from src.models import NewsItem, AnalyzedNews, NewsLightAnalysis
from src.agents.base_analyzer import BaseLightAnalyzer


class NewsLightAnalyzer(BaseLightAnalyzer[NewsItem, AnalyzedNews, NewsLightAnalysis]):
    """
    热点浅度分析器

    使用 LLM 对热点资讯进行结构化分析，支持异步批量处理。

    Usage:
        async with LLMClient() as client:
            analyzer = NewsLightAnalyzer(client)
            results = await analyzer.analyze_batch(news_items)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        language: Optional[str] = None,
    ):
        """
        初始化热点浅度分析器

        Args:
            llm_client: LLM 客户端实例
            language: 输出语言，默认从配置系统读取
        """
        super().__init__(llm_client, language)

    def _get_prompt_key(self) -> str:
        return "news"

    def _build_user_content(self, item: NewsItem) -> str:
        return self._user_prompt.format(
            title=item.title,
            source_name=item.source_name,
            summary=item.summary or "无摘要",
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
        return "热点分析"

    def _get_progress_unit(self) -> str:
        return "条"
