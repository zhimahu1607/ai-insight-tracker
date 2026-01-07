"""
热点数据模型

定义 RSS 源配置、热点条目、浅度分析结果等数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl

from .common import Keywords


class FetchType(str, Enum):
    """获取类型枚举"""
    RSS = "rss"
    CRAWLER = "crawler"


class RSSSource(BaseModel):
    """RSS 源配置"""

    name: str = Field(description='源名称, e.g., "Hacker News"')
    url: HttpUrl = Field(description="RSS Feed URL")
    category: str = Field(description="分类: tech/ai/product/news")
    language: str = Field(description="语言: en/zh")
    weight: float = Field(
        default=1.0, ge=0.0, le=1.0, description="权重 (用于排序)"
    )
    enabled: bool = Field(default=True, description="是否启用")


class NewsSource(BaseModel):
    """新闻源配置"""

    name: str = Field(description='公司名称, e.g., "OpenAI"')
    company: str = Field(description='公司标识符, e.g., "openai"')
    blog_url: HttpUrl = Field(description="博客/研究页面 URL")
    fetch_type: FetchType = Field(description="获取类型: rss/crawler")

    # RSS 专用字段
    rss_url: Optional[HttpUrl] = Field(
        default=None,
        description="RSS Feed URL (仅 fetch_type=rss 时需要)"
    )

    # Crawler 专用字段
    extractor: Optional[str] = Field(
        default=None,
        description="提取器名称 (仅 fetch_type=crawler 时需要)"
    )
    js_render: bool = Field(
        default=False,
        description="是否需要 JavaScript 渲染"
    )

    # 通用字段
    language: str = Field(default="en", description="语言: en/zh")
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="权重 (用于排序)"
    )
    enabled: bool = Field(default=True, description="是否启用")


class NewsItem(BaseModel):
    """热点条目模型"""

    id: str = Field(description="唯一标识 (URL hash)")
    title: str = Field(description="标题")
    url: HttpUrl = Field(description="原文链接")
    source_name: str = Field(description="来源名称")
    source_category: str = Field(description="来源分类")
    language: str = Field(description="语言")
    published: datetime = Field(description="发布时间")
    summary: Optional[str] = Field(default=None, description="原始摘要 (RSS 提供)")
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="来源权重 (继承自 RSSSource，用于排序)",
    )
    # 新闻源扩展字段
    fetch_type: FetchType = Field(
        default=FetchType.RSS,
        description="数据获取方式"
    )
    company: Optional[str] = Field(
        default=None,
        description="公司标识符"
    )


class NewsLightAnalysis(BaseModel):
    """热点浅度分析输出结构"""

    summary: str = Field(description="内容摘要，150-200 字")
    category: Literal["AI", "LLM", "开源", "产品", "行业", "其他"] = Field(
        description="细分类别"
    )
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="情感倾向"
    )
    keywords: Keywords = Field(
        default_factory=list, description="关键词列表，最多 5 个"
    )


class AnalyzedNews(NewsItem):
    """包含分析结果的热点"""

    light_analysis: Optional[NewsLightAnalysis] = Field(
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

