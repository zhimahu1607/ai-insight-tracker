"""Paper light analyzer."""

from src.agents.base_analyzer import BaseLightAnalyzer
from src.models import AnalyzedPaper, Paper, PaperLightAnalysis


class PaperLightAnalyzer(BaseLightAnalyzer[Paper, AnalyzedPaper, PaperLightAnalysis]):
    """Run structured light analysis for papers."""

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
        return "paper analysis"

    def _get_progress_unit(self) -> str:
        return "paper"
