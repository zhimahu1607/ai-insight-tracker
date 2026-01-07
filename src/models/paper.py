"""
论文数据模型

定义论文相关的数据结构，包括原始论文、浅度分析结果、带分析的完整论文。
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl

from .common import Tags


class Paper(BaseModel):
    """论文基础数据模型"""

    id: str = Field(description='arXiv ID, e.g., "2501.12345"')
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

