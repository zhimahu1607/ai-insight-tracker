"""
热点数据模型测试

测试 RSSSource, NewsItem, NewsLightAnalysis, AnalyzedNews 模型。
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.models import RSSSource, NewsItem, NewsLightAnalysis, AnalyzedNews


class TestRSSSource:
    """RSSSource 模型测试"""
    
    def test_valid_source(self, sample_rss_source_dict):
        """创建有效的 RSSSource 对象"""
        source = RSSSource(**sample_rss_source_dict)
        
        assert source.name == "Hacker News"
        assert str(source.url) == "https://news.ycombinator.com/rss"
        assert source.category == "tech"
        assert source.weight == 0.9
        assert source.enabled is True
    
    def test_weight_range_valid(self, sample_rss_source_dict):
        """weight 在 0-1 范围内"""
        sample_rss_source_dict["weight"] = 0.0
        source = RSSSource(**sample_rss_source_dict)
        assert source.weight == 0.0
        
        sample_rss_source_dict["weight"] = 1.0
        source = RSSSource(**sample_rss_source_dict)
        assert source.weight == 1.0
    
    def test_weight_out_of_range(self, sample_rss_source_dict):
        """weight 超出范围应该失败"""
        sample_rss_source_dict["weight"] = 1.5
        
        with pytest.raises(ValidationError):
            RSSSource(**sample_rss_source_dict)
    
    def test_weight_negative(self, sample_rss_source_dict):
        """负数 weight 应该失败"""
        sample_rss_source_dict["weight"] = -0.1
        
        with pytest.raises(ValidationError):
            RSSSource(**sample_rss_source_dict)
    
    def test_default_values(self):
        """默认值测试"""
        source = RSSSource(
            name="Test",
            url="https://example.com/rss",
            category="tech",
            language="en",
        )
        
        assert source.weight == 1.0
        assert source.enabled is True
    
    def test_invalid_url(self, sample_rss_source_dict):
        """无效 URL 应该失败"""
        sample_rss_source_dict["url"] = "not-a-url"
        
        with pytest.raises(ValidationError):
            RSSSource(**sample_rss_source_dict)


class TestNewsItem:
    """NewsItem 模型测试"""
    
    def test_valid_news_item(self, sample_news_item_dict):
        """创建有效的 NewsItem 对象"""
        news = NewsItem(**sample_news_item_dict)
        
        assert news.id == "abc123def456"
        assert news.title == "OpenAI Releases GPT-5 with Revolutionary Capabilities"
        assert news.source_name == "Hacker News"
        assert news.weight == 0.9
    
    def test_optional_summary(self, sample_news_item_dict):
        """summary 可以为 None"""
        sample_news_item_dict["summary"] = None
        
        news = NewsItem(**sample_news_item_dict)
        assert news.summary is None
    
    def test_serialization(self, sample_news_item):
        """序列化和反序列化"""
        json_str = sample_news_item.model_dump_json()
        restored = NewsItem.model_validate_json(json_str)
        
        assert restored.id == sample_news_item.id
        assert restored.title == sample_news_item.title


class TestNewsLightAnalysis:
    """NewsLightAnalysis 模型测试"""
    
    def test_valid_analysis(self, sample_news_light_analysis_dict):
        """创建有效的 NewsLightAnalysis 对象"""
        analysis = NewsLightAnalysis(**sample_news_light_analysis_dict)
        
        assert "OpenAI" in analysis.summary
        assert "GPT-5" in analysis.summary
        assert analysis.category == "AI"
        assert analysis.sentiment == "positive"
        assert len(analysis.keywords) == 4
    
    def test_category_values(self, sample_news_light_analysis_dict):
        """category 枚举值验证"""
        valid_categories = ["AI", "LLM", "开源", "产品", "行业", "其他"]
        
        for cat in valid_categories:
            sample_news_light_analysis_dict["category"] = cat
            analysis = NewsLightAnalysis(**sample_news_light_analysis_dict)
            assert analysis.category == cat
    
    def test_invalid_category(self, sample_news_light_analysis_dict):
        """无效 category 应该失败"""
        sample_news_light_analysis_dict["category"] = "invalid"
        
        with pytest.raises(ValidationError):
            NewsLightAnalysis(**sample_news_light_analysis_dict)
    
    def test_sentiment_values(self, sample_news_light_analysis_dict):
        """sentiment 枚举值验证"""
        valid_sentiments = ["positive", "neutral", "negative"]
        
        for sent in valid_sentiments:
            sample_news_light_analysis_dict["sentiment"] = sent
            analysis = NewsLightAnalysis(**sample_news_light_analysis_dict)
            assert analysis.sentiment == sent
    
    def test_invalid_sentiment(self, sample_news_light_analysis_dict):
        """无效 sentiment 应该失败"""
        sample_news_light_analysis_dict["sentiment"] = "invalid"
        
        with pytest.raises(ValidationError):
            NewsLightAnalysis(**sample_news_light_analysis_dict)
    
    def test_keywords_max_length(self, sample_news_light_analysis_dict):
        """keywords 最多 5 个"""
        sample_news_light_analysis_dict["keywords"] = ["k1", "k2", "k3", "k4", "k5", "k6"]
        
        with pytest.raises(ValidationError):
            NewsLightAnalysis(**sample_news_light_analysis_dict)
    
    def test_keywords_empty(self, sample_news_light_analysis_dict):
        """空 keywords 应该通过"""
        sample_news_light_analysis_dict["keywords"] = []
        
        analysis = NewsLightAnalysis(**sample_news_light_analysis_dict)
        assert analysis.keywords == []


class TestAnalyzedNews:
    """AnalyzedNews 模型测试"""
    
    def test_valid_analyzed_news(self, sample_analyzed_news):
        """创建有效的 AnalyzedNews 对象"""
        assert sample_analyzed_news.id == "abc123def456"
        assert sample_analyzed_news.analysis_status == "success"
        assert sample_analyzed_news.light_analysis is not None
        assert sample_analyzed_news.analyzed_at is not None
    
    def test_is_analyzed_property_success(self, sample_analyzed_news):
        """分析成功时 is_analyzed 为 True"""
        assert sample_analyzed_news.is_analyzed is True
    
    def test_is_analyzed_property_pending(self, sample_news_item_dict):
        """待分析时 is_analyzed 为 False"""
        news = AnalyzedNews(
            **sample_news_item_dict,
            analysis_status="pending",
        )
        
        assert news.is_analyzed is False
    
    def test_is_analyzed_property_failed(self, sample_news_item_dict):
        """分析失败时 is_analyzed 为 False"""
        news = AnalyzedNews(
            **sample_news_item_dict,
            analysis_status="failed",
            analysis_error="Parse error",
        )
        
        assert news.is_analyzed is False
    
    def test_status_transitions(self, sample_news_item_dict):
        """分析状态值验证"""
        for status in ["pending", "success", "failed"]:
            news = AnalyzedNews(**sample_news_item_dict, analysis_status=status)
            assert news.analysis_status == status
    
    def test_serialization(self, sample_analyzed_news):
        """序列化和反序列化"""
        json_str = sample_analyzed_news.model_dump_json()
        restored = AnalyzedNews.model_validate_json(json_str)
        
        assert restored.id == sample_analyzed_news.id
        assert restored.is_analyzed == sample_analyzed_news.is_analyzed

