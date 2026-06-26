"""
论文数据模型

定义论文相关的数据结构，包括原始论文、浅度分析结果、带分析的完整论文。
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl

from .common import Tags


QualityConfidence = Literal["high", "medium", "low"]


class PaperExternalIds(BaseModel):
    """论文在外部学术数据库中的标识。"""

    arxiv: Optional[str] = Field(default=None, description="arXiv ID")
    doi: Optional[str] = Field(default=None, description="DOI")
    semantic_scholar: Optional[str] = Field(
        default=None, description="Semantic Scholar paperId"
    )
    openalex: Optional[str] = Field(default=None, description="OpenAlex work ID")
    openreview: Optional[str] = Field(default=None, description="OpenReview forum/note ID")


class SemanticScholarSignal(BaseModel):
    """Semantic Scholar 返回的论文质量信号。"""

    paper_id: str = Field(description="Semantic Scholar paperId")
    citation_count: int = Field(default=0, description="引用数")
    influential_citation_count: int = Field(default=0, description="高影响引用数")
    reference_count: int = Field(default=0, description="参考文献数")
    venue: Optional[str] = Field(default=None, description="发表 venue")
    publication_types: list[str] = Field(default_factory=list, description="发表类型")
    fields_of_study: list[str] = Field(default_factory=list, description="研究领域")
    tldr: Optional[str] = Field(default=None, description="Semantic Scholar TLDR")


class CodeRepositorySignal(BaseModel):
    """论文关联代码仓库信号。"""

    url: str = Field(description="仓库 URL")
    owner: Optional[str] = Field(default=None, description="仓库 owner")
    name: Optional[str] = Field(default=None, description="仓库名称")
    stars: int = Field(default=0, description="GitHub stars")
    framework: Optional[str] = Field(default=None, description="主要框架")
    is_official: Optional[bool] = Field(default=None, description="是否官方实现")


class PapersWithCodeSignal(BaseModel):
    """Papers with Code 返回的工程复现信号。"""

    paper_id: str = Field(description="Papers with Code paper ID")
    has_code: bool = Field(default=False, description="是否有关联代码")
    repositories: list[CodeRepositorySignal] = Field(default_factory=list)


class OpenAlexSignal(BaseModel):
    """OpenAlex 返回的开放学术图谱信号。"""

    work_id: str = Field(description="OpenAlex work ID")
    cited_by_count: int = Field(default=0, description="引用数")
    fwci: Optional[float] = Field(default=None, description="Field-weighted citation impact")
    institutions: list[str] = Field(default_factory=list, description="作者机构")
    topics: list[str] = Field(default_factory=list, description="主题")
    source: Optional[str] = Field(default=None, description="发表来源")


class OpenReviewSignal(BaseModel):
    """OpenReview 返回的审稿和录用信号。"""

    forum_id: str = Field(description="OpenReview forum ID")
    venue_id: Optional[str] = Field(default=None, description="Venue ID")
    decision: Optional[str] = Field(default=None, description="录用决定")
    rating_avg: Optional[float] = Field(default=None, description="平均评分")
    confidence_avg: Optional[float] = Field(default=None, description="平均 confidence")
    review_count: int = Field(default=0, description="官方 review 数")


class PaperQualitySignals(BaseModel):
    """外部质量信号集合。"""

    sources: list[str] = Field(default_factory=list, description="命中的外部信号源")
    fetched_at: Optional[datetime] = Field(default=None, description="信号获取时间")
    semantic_scholar: Optional[SemanticScholarSignal] = None
    papers_with_code: Optional[PapersWithCodeSignal] = None
    openalex: Optional[OpenAlexSignal] = None
    openreview: Optional[OpenReviewSignal] = None


class Paper(BaseModel):
    """论文基础数据模型"""

    id: str = Field(description='arXiv ID, e.g., "2501.12345"')
    source: str = Field(default="arxiv", description="论文来源，如 arxiv/openreview/proceedings")
    external_ids: PaperExternalIds = Field(default_factory=PaperExternalIds)
    title: str = Field(description="论文标题")
    authors: list[str] = Field(description="作者列表")
    abstract: str = Field(description="摘要原文")
    categories: list[str] = Field(description='arXiv 分类, e.g., ["cs.AI", "cs.CL"]')
    primary_category: str = Field(description="主分类")
    pdf_url: HttpUrl = Field(description="PDF 链接")
    abs_url: HttpUrl = Field(description="摘要页链接")
    published: datetime = Field(description="发布时间（首次提交）")
    updated: Optional[datetime] = Field(default=None, description="最后更新时间")
    comment: Optional[str] = Field(default=None, description="作者备注（如会议信息）")
    quality_signals: Optional[PaperQualitySignals] = Field(
        default=None, description="外部质量信号"
    )
    quality_score: Optional[float] = Field(
        default=None, ge=0, le=100, description="外部质量分，0-100"
    )
    relevance_score: Optional[float] = Field(
        default=None, ge=0, le=100, description="与追踪方向的相关性分，0-100"
    )
    tracking_score: Optional[float] = Field(
        default=None, ge=0, le=100, description="最终追踪分，0-100"
    )
    quality_confidence: QualityConfidence = Field(
        default="low", description="质量信号置信度"
    )
    quality_reasons: list[str] = Field(
        default_factory=list, description="入选或降权的可解释原因"
    )


class PaperLightAnalysis(BaseModel):
    """论文浅度分析输出结构"""

    overview: str = Field(description="一句话总结论文核心贡献，不超过 50 字")
    motivation: str = Field(description="研究动机：为什么做这个研究，解决什么问题，100-150 字")
    method: str = Field(description="研究方法：采用了什么技术或方法，100-150 字")
    result: str = Field(description="主要结果：取得了什么效果或发现，100-150 字")
    conclusion: str = Field(description="结论：主要贡献和意义，100-150 字")
    tags: Tags = Field(
        description="3-5 个具体的技术标签（如：Large Language Model, Reinforcement Learning, Self-Attention）"
    )


class AnalyzedPaper(Paper):
    """包含分析结果的论文"""

    light_analysis: Optional[PaperLightAnalysis] = Field(
        default=None, description="浅度分析结果"
    )
    analyzed_at: Optional[datetime] = Field(default=None, description="分析完成时间")
    analysis_status: Literal["success", "failed", "pending"] = Field(
        default="pending", description="分析状态"
    )
    analysis_error: Optional[str] = Field(
        default=None, description="失败时的错误信息"
    )

    @property
    def is_analyzed(self) -> bool:
        """是否已成功分析"""
        return self.analysis_status == "success" and self.light_analysis is not None

