"""
配置数据模型测试

测试 LLMConfig, ArxivConfig, Settings 等配置模型。
"""

import pytest
from pydantic import ValidationError

from src.config.models import (
    LLMConfig,
    ArxivConfig,
    SearchConfig,
    AnalysisConfig,
    NotificationConfig,
    NewsFetcherConfig,
    AdvancedConfig,
    Settings,
)


class TestLLMConfig:
    """LLMConfig 模型测试"""
    
    def test_default_values(self):
        """默认值测试"""
        config = LLMConfig()
        
        assert config.provider == ""
        assert config.model == ""
        assert config.api_key == ""
    
    def test_with_values(self):
        """带值创建"""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key="sk-test-key",
        )
        
        assert config.provider == "openai"
        assert config.model == "gpt-4"


class TestArxivConfig:
    """ArxivConfig 模型测试"""
    
    def test_default_values(self):
        """默认值测试"""
        config = ArxivConfig()
        
        assert config.categories == ["cs.AI", "cs.CL", "cs.CV", "cs.LG"]
        assert config.max_results == 100
        assert config.request_delay == 3.0
        assert config.timeout == 60.0
    
    def test_custom_categories(self):
        """自定义分类"""
        config = ArxivConfig(categories=["cs.AI", "stat.ML"])
        
        assert config.categories == ["cs.AI", "stat.ML"]


class TestSearchConfig:
    """SearchConfig 模型测试"""
    
    def test_default_values(self):
        """默认值测试"""
        config = SearchConfig()
        
        assert config.api == "tavily"
        assert config.tavily_api_key == ""
        assert config.max_results == 5
        assert config.timeout == 30


class TestAnalysisConfig:
    """AnalysisConfig 模型测试"""
    
    def test_default_values(self):
        """默认值测试"""
        config = AnalysisConfig()
        
        assert config.max_concurrent == 20
        assert config.timeout == 60
        assert config.max_research_iterations == 5
        assert config.max_write_iterations == 3


class TestNotificationConfig:
    """NotificationConfig 模型测试"""
    
    def test_default_values(self):
        """默认值测试"""
        config = NotificationConfig()
        
        assert config.feishu_webhook_url == ""
        assert config.language == "zh"
        assert config.max_papers == 10
        assert config.max_news == 5


class TestNewsFetcherConfig:
    """NewsFetcherConfig 模型测试"""

    def test_github_trending_defaults(self):
        """GitHub Trending 默认配置"""
        config = NewsFetcherConfig()

        assert config.github_trending_enabled is True
        assert config.github_trending_since == "weekly"
        assert config.github_trending_language == ""
        assert config.github_trending_limit == 25
        assert config.github_trending_min_stars == 1000
        assert config.github_trending_weight == 0.9
        assert config.github_trending_readme_max_chars == 8000

    def test_github_trending_weight_range(self):
        """GitHub Trending 权重范围验证"""
        with pytest.raises(ValidationError):
            NewsFetcherConfig(github_trending_weight=1.1)


class TestAdvancedConfig:
    """AdvancedConfig 模型测试"""
    
    def test_default_values(self):
        """默认值测试"""
        config = AdvancedConfig()
        
        assert config.llm_timeout == 60
        assert config.llm_max_retries == 3
        assert config.rss_hours == 24
        assert config.rss_max_concurrent == 20


class TestSettings:
    """Settings 模型测试"""
    
    def test_default_values(self):
        """默认值测试"""
        settings = Settings()
        
        assert settings.llm.provider == ""
        assert settings.arxiv.max_results == 100
        assert settings.analysis.max_concurrent == 20
    
    def test_validate_required_all_present(self):
        """所有必填项存在时验证通过"""
        settings = Settings(
            llm=LLMConfig(
                provider="deepseek",
                model="deepseek-v4-pro",
                api_key="test-key",
            )
        )
        
        # 不应该抛出异常
        settings.validate_required()
    
    def test_validate_required_missing_provider(self):
        """缺少 provider 时验证失败"""
        settings = Settings(
            llm=LLMConfig(
                provider="",
                model="deepseek-v4-pro",
                api_key="test-key",
            )
        )
        
        with pytest.raises(ValueError, match="llm.provider 是必填项"):
            settings.validate_required()
    
    def test_validate_required_missing_model(self):
        """缺少 model 时验证失败"""
        settings = Settings(
            llm=LLMConfig(
                provider="deepseek",
                model="",
                api_key="test-key",
            )
        )
        
        with pytest.raises(ValueError, match="llm.model 是必填项"):
            settings.validate_required()
    
    def test_validate_required_missing_api_key(self):
        """缺少 api_key 时验证失败"""
        settings = Settings(
            llm=LLMConfig(
                provider="deepseek",
                model="deepseek-v4-pro",
                api_key="",
            )
        )
        
        with pytest.raises(ValueError, match="llm.api_key 是必填项"):
            settings.validate_required()
    
    def test_validate_required_multiple_errors(self):
        """多个必填项缺失"""
        settings = Settings()
        
        with pytest.raises(ValueError) as exc_info:
            settings.validate_required()
        
        error_msg = str(exc_info.value)
        assert "llm.provider" in error_msg
        assert "llm.model" in error_msg
        assert "llm.api_key" in error_msg
    
    def test_get_api_key(self):
        """get_api_key 方法测试"""
        settings = Settings(
            llm=LLMConfig(api_key="my-secret-key")
        )
        
        assert settings.get_api_key() == "my-secret-key"
    
    def test_get_api_key_empty(self):
        """未配置 API Key 时返回空字符串"""
        settings = Settings()
        
        assert settings.get_api_key() == ""
