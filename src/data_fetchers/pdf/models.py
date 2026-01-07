"""
PDF 解析数据模型

定义论文 PDF 解析后的结构化数据模型。
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SectionType(str, Enum):
    """论文章节类型"""

    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHOD = "method"
    EXPERIMENT = "experiment"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    APPENDIX = "appendix"
    OTHER = "other"


class PaperSection(BaseModel):
    """论文章节"""

    section_type: SectionType = Field(description="章节类型")
    title: str = Field(description="章节标题")
    content: str = Field(description="章节内容")
    page_start: int = Field(description="起始页码")
    page_end: int = Field(description="结束页码")
    token_count: int = Field(default=0, description="估算 token 数")


class TableInfo(BaseModel):
    """表格信息"""

    table_id: str = Field(description="表格编号，如 Table 1")
    caption: Optional[str] = Field(default=None, description="表格说明")
    page: int = Field(description="所在页码")
    headers: list[str] = Field(default_factory=list, description="表头")
    rows: list[list[str]] = Field(default_factory=list, description="数据行")
    raw_text: str = Field(default="", description="表格原始文本表示")


class FigureInfo(BaseModel):
    """图表信息"""

    figure_id: str = Field(description="图表编号，如 Figure 1")
    caption: str = Field(description="图表说明")
    page: int = Field(description="所在页码")


class Reference(BaseModel):
    """参考文献"""

    index: int = Field(description="引用编号")
    raw_text: str = Field(description="原始引用文本")
    title: Optional[str] = Field(default=None, description="解析后的标题")
    authors: Optional[list[str]] = Field(default=None, description="作者列表")
    year: Optional[int] = Field(default=None, description="发表年份")
    arxiv_id: Optional[str] = Field(default=None, description="arXiv ID（如有）")
    doi: Optional[str] = Field(default=None, description="DOI（如有）")


class ParsedPaper(BaseModel):
    """解析后的论文完整结构"""

    paper_id: str = Field(description="arXiv ID")
    title: str = Field(description="论文标题")

    # 全文内容
    full_text: str = Field(default="", description="完整文本（用于简单场景）")
    total_pages: int = Field(default=0, description="总页数")
    total_tokens: int = Field(default=0, description="估算总 token 数")

    # 结构化内容
    sections: list[PaperSection] = Field(
        default_factory=list, description="按章节分块的内容"
    )
    tables: list[TableInfo] = Field(default_factory=list, description="表格信息列表")
    figures: list[FigureInfo] = Field(default_factory=list, description="图表信息列表")
    references: list[Reference] = Field(
        default_factory=list, description="参考文献列表"
    )

    # 元信息
    parse_status: str = Field(default="success", description="解析状态")
    parse_error: Optional[str] = Field(default=None, description="解析错误信息")

    @property
    def has_content(self) -> bool:
        """是否有有效内容"""
        return self.parse_status == "success" and len(self.sections) > 0

