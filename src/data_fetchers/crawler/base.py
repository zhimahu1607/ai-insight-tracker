"""
提取器基类

每个网站需要实现专用提取器，继承此基类。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from typing import Optional, Any

from src.models import NewsItem, NewsSource
from src.data_fetchers.text_utils import clean_html_to_text


@dataclass(frozen=True)
class DetailPageFields:
    """
    详情页提取结果（结构化）

    - title: 通常来自详情页 <h1>
    - content: 正文纯文本（尽量完整）
    - date: 可选的日期文本（不同站点格式各异，这里不强制解析）
    """

    title: Optional[str] = None
    content: Optional[str] = None
    date: Optional[str] = None


class BaseExtractor(ABC):
    """
    网站内容提取器基类

    每个网站需要实现：
    1. get_extraction_schema(): 返回 CSS 提取 Schema
    2. parse_result(): 将爬取结果解析为 NewsItem 列表
    3. get_js_code() (可选): 返回需要执行的 JavaScript 代码
    """

    @abstractmethod
    def get_extraction_schema(self) -> dict:
        """
        返回内容提取 Schema

        使用 JsonCssExtractionStrategy 的 schema 格式:
        {
            "name": "Schema Name",
            "baseSelector": "article.item",
            "fields": [
                {"name": "title", "selector": "h2", "type": "text"},
                {"name": "url", "selector": "a", "type": "attribute", "attribute": "href"},
            ]
        }
        """
        pass

    @abstractmethod
    def parse_result(
        self,
        extracted_content: str,
        source: NewsSource,
    ) -> list[NewsItem]:
        """
        解析爬取结果为 NewsItem 列表

        Args:
            extracted_content: crawl4ai 提取的 JSON 字符串
            source: 源配置

        Returns:
            NewsItem 列表
        """
        pass

    # ------------------------------
    # 详情页（全文）抓取：可选实现
    # ------------------------------
    def get_detail_extraction_schema(self) -> Optional[dict]:
        """
        返回详情页正文提取 Schema（可选）。

        如果返回 None，则 crawler 只抓列表页，不会逐篇抓正文。
        """
        return None

    def parse_detail_result(
        self,
        extracted_content: str,
        source: NewsSource,
    ) -> Optional[str]:
        """
        将详情页提取结果解析为正文纯文本（可选）。

        Returns:
            正文文本，None 表示未提取到。
        """
        fields = self.parse_detail_fields(extracted_content, source)
        return fields.content if fields else None

    def parse_detail_fields(
        self,
        extracted_content: str,
        source: NewsSource,
    ) -> Optional[DetailPageFields]:
        """
        将详情页提取结果解析为结构化字段（默认实现）。

        默认假设 crawl4ai JsonCssExtractionStrategy 返回 JSON：
        - list[dict]：常见，取第 0 个元素
        - dict：少数情况
        """
        _ = source
        if not extracted_content:
            return None
        try:
            data = json.loads(extracted_content)
        except json.JSONDecodeError:
            return None

        record: Optional[dict[str, Any]] = None
        if isinstance(data, list) and data and isinstance(data[0], dict):
            record = data[0]
        elif isinstance(data, dict):
            record = data

        if not record:
            return None

        raw_title = record.get("title")
        raw_content = record.get("content")
        raw_date = record.get("date")

        title = clean_html_to_text(str(raw_title)).strip() if raw_title else None
        content = clean_html_to_text(str(raw_content)) if raw_content else None
        date = clean_html_to_text(str(raw_date)).strip() if raw_date else None

        if not title and not content and not date:
            return None

        return DetailPageFields(title=title or None, content=content or None, date=date or None)

    def get_detail_js_code(self) -> Optional[str]:
        """详情页需要执行的 JS（可选），默认复用不执行。"""
        return None

    def get_js_code(self) -> Optional[str]:
        """
        返回需要执行的 JavaScript 代码

        用于：
        - 触发懒加载
        - 展开折叠内容
        - 点击 "加载更多" 按钮

        Returns:
            JavaScript 代码字符串，None 表示不需要
        """
        return None

    def get_base_url(self) -> str:
        """
        返回基础 URL，用于补全相对链接

        子类可以覆盖此方法
        """
        return ""

