"""
热点浅度分析器测试

测试 NewsLightAnalyzer 类。
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.news.light_analyzer import NewsLightAnalyzer
from src.models import NewsItem, NewsLightAnalysis, AnalyzedNews
from src.llm.exceptions import LLMParseError, LLMRateLimitError


class TestNewsLightAnalyzerInit:
    """NewsLightAnalyzer 初始化测试"""
    
    def test_init_with_client(self, mock_settings):
        """使用 LLM 客户端初始化"""
        mock_client = MagicMock()
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore"):
                analyzer = NewsLightAnalyzer(mock_client)
        
        assert analyzer._llm_client is mock_client
        assert analyzer._language == "zh"
    
    def test_init_with_custom_language(self, mock_settings):
        """自定义语言"""
        mock_client = MagicMock()
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore"):
                analyzer = NewsLightAnalyzer(mock_client, language="en")
        
        assert analyzer._language == "en"


class TestNewsLightAnalyzerBuildPrompt:
    """_build_prompt 方法测试"""
    
    def test_build_prompt_structure(self, mock_settings, sample_news_item):
        """构建 Prompt 结构"""
        mock_client = MagicMock()
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore"):
                analyzer = NewsLightAnalyzer(mock_client)
                messages = analyzer._build_prompt(sample_news_item)
        
        # LangChain messages 使用 type 属性
        assert len(messages) == 2
        assert messages[0].type == "system"
        assert messages[1].type == "human"
    
    def test_build_prompt_contains_news_info(self, mock_settings, sample_news_item):
        """Prompt 包含热点信息"""
        mock_client = MagicMock()
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore"):
                analyzer = NewsLightAnalyzer(mock_client)
                messages = analyzer._build_prompt(sample_news_item)
        
        user_content = messages[1].content
        assert sample_news_item.title in user_content
        assert sample_news_item.source_name in user_content


class TestNewsLightAnalyzerAnalyzeOne:
    """analyze_one 方法测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_success(
        self,
        mock_settings,
        sample_news_item,
        sample_news_light_analysis,
    ):
        """分析成功"""
        mock_client = AsyncMock()
        mock_client.chat_structured = AsyncMock(return_value=sample_news_light_analysis)
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore", return_value=AsyncMock()):
                analyzer = NewsLightAnalyzer(mock_client)
                analyzer._semaphore = MagicMock()
                analyzer._semaphore.__aenter__ = AsyncMock()
                analyzer._semaphore.__aexit__ = AsyncMock()
                
                result = await analyzer.analyze_one(sample_news_item)
        
        # ✅ 验证 LLM 被调用
        mock_client.chat_structured.assert_called_once()
        
        # 验证调用参数
        call_args = mock_client.chat_structured.call_args
        assert call_args is not None
        
        assert isinstance(result, AnalyzedNews)
        assert result.analysis_status == "success"
        assert result.light_analysis is not None
        assert result.analyzed_at is not None
    
    @pytest.mark.asyncio
    async def test_analyze_parse_error(self, mock_settings, sample_news_item):
        """解析错误标记失败状态"""
        mock_client = AsyncMock()
        mock_client.chat_structured = AsyncMock(
            side_effect=LLMParseError("Parse failed", raw_response="{}")
        )
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore", return_value=AsyncMock()):
                analyzer = NewsLightAnalyzer(mock_client)
                analyzer._semaphore = MagicMock()
                analyzer._semaphore.__aenter__ = AsyncMock()
                analyzer._semaphore.__aexit__ = AsyncMock()
                
                result = await analyzer.analyze_one(sample_news_item)
        
        # ✅ 验证 LLM 被调用（即使失败也要尝试调用）
        mock_client.chat_structured.assert_called_once()
        
        assert result.analysis_status == "failed"
        # 错误消息可能是原始异常消息或包装后的消息
        assert result.analysis_error is not None


class TestNewsLightAnalyzerAnalyzeBatch:
    """analyze_batch 方法测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_batch_empty(self, mock_settings):
        """空输入返回空列表"""
        mock_client = AsyncMock()
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore"):
                analyzer = NewsLightAnalyzer(mock_client)
                result = await analyzer.analyze_batch([])
        
        assert result == []


class TestNewsLightAnalyzerGetStats:
    """get_analysis_stats 静态方法测试"""
    
    def test_stats_all_success(self, sample_analyzed_news):
        """全部成功"""
        news = [sample_analyzed_news, sample_analyzed_news]
        
        stats = NewsLightAnalyzer.get_analysis_stats(news)
        
        assert stats["total"] == 2
        assert stats["success"] == 2
        assert stats["failed"] == 0
        assert stats["success_rate"] == 1.0
    
    def test_stats_partial_failure(self, sample_news_item_dict):
        """部分失败"""
        success = AnalyzedNews(**sample_news_item_dict, analysis_status="success")
        
        sample_news_item_dict["id"] = "failed123"
        failed = AnalyzedNews(**sample_news_item_dict, analysis_status="failed")
        
        news = [success, failed]
        
        stats = NewsLightAnalyzer.get_analysis_stats(news)
        
        assert stats["total"] == 2
        assert stats["success"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.5
    
    def test_stats_empty(self):
        """空列表"""
        stats = NewsLightAnalyzer.get_analysis_stats([])
        
        assert stats["total"] == 0
        assert stats["success"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 1.0

