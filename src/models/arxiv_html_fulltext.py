"""
arXiv 官方 HTML 全文结构化数据模型

目标结构参考: data/arxiv_html_fulltext_*.json
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class ArxivHtmlSource(BaseModel):
    provider: Literal["arxiv"] = Field(default="arxiv", description="数据来源提供方")
    url: HttpUrl = Field(description="全文 HTML URL")
    fetched_at: datetime = Field(description="抓取时间（UTC）")


class ArxivHtmlSection(BaseModel):
    level: int = Field(description="标题层级（对齐 HTML h2->2, h3->3 ...）")
    heading: str = Field(description="原始标题文本（含编号，如 '1 Introduction'）")
    number: Optional[str] = Field(
        default=None, description="章节编号（如 '3.2'；无编号则为 null）"
    )
    title: str = Field(description="章节标题（去掉编号部分）")
    paragraphs: list[str] = Field(default_factory=list, description="段落文本数组（纯文本）")
    children: list["ArxivHtmlSection"] = Field(default_factory=list, description="子章节")


class ArxivHtmlStats(BaseModel):
    html_chars: int = Field(description="HTML 原文字符数")
    blocks: int = Field(description="解析得到的块数量（标题+段落等的统计）")


class ArxivHtmlFulltext(BaseModel):
    paper_id: str = Field(description="arXiv ID（不含版本号）")
    source: ArxivHtmlSource = Field(description="来源信息")
    title: str = Field(description="论文标题")
    authors: list[str] = Field(default_factory=list, description="作者列表")
    keywords: list[str] = Field(default_factory=list, description="关键词（若无法解析则为空）")
    abstract: str = Field(default="", description="摘要")
    front_matter_paragraphs: list[str] = Field(
        default_factory=list, description="正文前置段落（非章节正文）"
    )
    sections: list[ArxivHtmlSection] = Field(default_factory=list, description="章节树")
    stats: ArxivHtmlStats = Field(description="统计信息")


