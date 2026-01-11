"""
配置数据模型

使用 Pydantic v2 定义配置结构，提供类型安全和数据验证。
"""

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """
    LLM 配置

    provider 和 model 为必填项，无默认值。
    验证逻辑在 Settings.validate_required() 中实现。
    """

    provider: str = Field(default="", description="LLM 提供商（必填）")
    model: str = Field(default="", description="LLM 模型（必填）")
    api_key: str = Field(default="", description="API Key（必填）")


class ArxivConfig(BaseModel):
    """arXiv 数据获取配置"""

    categories: list[str] = Field(
        default=["cs.AI", "cs.CL", "cs.CV", "cs.LG"],
        description="要获取的 arXiv 分类列表",
    )
    max_results: int = Field(default=100, description="单次请求最大返回数（分页时为每页大小）")
    max_pages: int = Field(default=20, description="每个分类最多分页次数（安全上限）")
    request_delay: float = Field(
        default=3.0, description="请求间隔（秒），遵守 arXiv 限流规则"
    )
    timeout: float = Field(default=60.0, description="HTTP 请求超时（秒）")


class SearchConfig(BaseModel):
    """搜索工具配置（深度分析使用）"""

    api: str = Field(default="tavily", description="搜索 API: tavily / duckduckgo")
    tavily_api_key: str = Field(
        default="", description="Tavily API Key（使用 Tavily 时必填）"
    )
    max_results: int = Field(default=5, description="每次搜索返回的结果数")
    timeout: int = Field(default=30, description="搜索请求超时（秒）")


class AnalysisConfig(BaseModel):
    """分析模块配置"""

    max_concurrent: int = Field(default=20, description="浅度分析最大并发数")
    timeout: int = Field(default=60, description="单次分析超时（秒）")
    max_research_iterations: int = Field(
        default=5, description="深度分析：最大研究迭代次数"
    )
    max_write_iterations: int = Field(
        default=3, description="深度分析：最大写作修改次数"
    )


class NotificationConfig(BaseModel):
    """通知配置"""

    feishu_webhook_url: str = Field(default="", description="飞书 Webhook URL")
    site_url: str = Field(default="", description="网站 URL（用于飞书卡片按钮跳转）")
    language: str = Field(default="zh", description="输出语言: zh / en")
    max_papers: int = Field(default=10, description="卡片中显示的论文数量")
    max_news: int = Field(default=5, description="卡片中显示的热点数量")
    timeout: int = Field(default=30, description="请求超时（秒）")
    max_retries: int = Field(default=3, description="最大重试次数")


class NewsFetcherConfig(BaseModel):
    """新闻源获取配置"""

    hours: int = Field(default=168, description="时间窗口（小时），默认 7 天")
    rss_timeout: float = Field(default=30.0, description="RSS 请求超时（秒）")
    rss_max_concurrent: int = Field(default=10, description="RSS 最大并发数")
    crawler_max_concurrent: int = Field(
        default=3, description="Crawler 最大并发数（浏览器实例数）"
    )
    crawler_timeout: float = Field(default=60.0, description="页面加载超时（秒）")
    headless: bool = Field(default=True, description="是否使用无头浏览器")


class AdvancedConfig(BaseModel):
    """高级配置"""

    llm_timeout: int = Field(default=60, description="LLM 请求超时（秒）")
    llm_max_retries: int = Field(default=3, description="LLM 最大重试次数")
    rss_hours: int = Field(default=24, description="RSS 获取时间窗口（小时）")
    rss_max_concurrent: int = Field(default=20, description="RSS 最大并发数")
    rss_timeout: float = Field(default=30.0, description="RSS HTTP 请求超时（秒）")


class Settings(BaseModel):
    """完整配置模型"""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    arxiv: ArxivConfig = Field(default_factory=ArxivConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    news: NewsFetcherConfig = Field(default_factory=NewsFetcherConfig)
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)

    def validate_required(self) -> None:
        """
        验证必填配置项

        在配置加载完成后调用此方法验证必填字段。
        验证失败时抛出 ValueError。

        Raises:
            ValueError: 当必填配置缺失时
        """
        errors: list[str] = []

        if not self.llm.provider:
            errors.append(
                "llm.provider 是必填项，请在配置文件或环境变量 LLM_PROVIDER 中设置"
            )
        if not self.llm.model:
            errors.append(
                "llm.model 是必填项，请在配置文件或环境变量 LLM_MODEL 中设置"
            )
        if not self.llm.api_key:
            errors.append(
                "llm.api_key 是必填项，请在配置文件或环境变量 LLM_API_KEY 中设置"
            )

        if errors:
            raise ValueError(
                "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            )

    def get_api_key(self) -> str:
        """
        获取 API Key

        Returns:
            API Key 字符串，未配置时返回空字符串
        """
        return self.llm.api_key

