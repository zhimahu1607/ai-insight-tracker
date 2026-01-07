"""
论文浅度分析器

继承 BaseLightAnalyzer，实现论文特定的分析逻辑。
"""

from typing import Optional

from src.llm import LLMClient
from src.models import Paper, AnalyzedPaper, PaperLightAnalysis
from src.agents.base_analyzer import BaseLightAnalyzer


class PaperLightAnalyzer(BaseLightAnalyzer[Paper, AnalyzedPaper, PaperLightAnalysis]):
    """
    论文浅度分析器

    使用 LLM 对论文摘要进行结构化分析，支持异步批量处理。

    Usage:
        async with LLMClient() as client:
            analyzer = PaperLightAnalyzer(client)
            results = await analyzer.analyze_batch(papers)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        language: Optional[str] = None,
    ):
        """
        初始化论文浅度分析器

        Args:
            llm_client: LLM 客户端实例
            language: 输出语言，默认从配置系统读取
        """
        super().__init__(llm_client, language)

    def _get_prompt_key(self) -> str:
        return "paper"

    def _build_user_content(self, item: Paper) -> str:
        return self._user_prompt.format(
            title=item.title,
            abstract=item.abstract,
        )

    def _create_output(self, item: Paper) -> AnalyzedPaper:
        return AnalyzedPaper(
            **item.model_dump(),
            analysis_status="pending",
        )

    def _get_analysis_schema(self) -> type[PaperLightAnalysis]:
        return PaperLightAnalysis

    def _set_analysis_result(
        self,
        output: AnalyzedPaper,
        analysis: PaperLightAnalysis,
    ) -> None:
        output.light_analysis = analysis

    def _get_item_id(self, item: Paper) -> str:
        return item.id

    def _get_progress_desc(self) -> str:
        return "论文分析"

    def _get_progress_unit(self) -> str:
        return "篇"
