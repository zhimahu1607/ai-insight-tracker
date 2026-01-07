"""
提取器基类

每个网站需要实现专用提取器，继承此基类。
"""

from abc import ABC, abstractmethod
from typing import Optional, Any

from src.models import NewsItem, NewsSource


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

