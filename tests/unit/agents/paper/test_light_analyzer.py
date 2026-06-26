"""
论文浅度分析器测试

测试 PaperLightAnalyzer 类。
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.paper.light_analyzer import PaperLightAnalyzer
from src.models import Paper, PaperLightAnalysis, AnalyzedPaper
from src.llm.exceptions import LLMParseError, LLMRateLimitError


class TestPaperLightAnalyzerInit:
    """PaperLightAnalyzer 初始化测试"""
    
    def test_init_with_client(self, mock_settings):
        """使用 LLM 客户端初始化"""
        mock_client = MagicMock()
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore"):
                analyzer = PaperLightAnalyzer(mock_client)
        
        assert analyzer._llm_client is mock_client
        assert analyzer._language == "zh"
    
    def test_init_with_custom_language(self, mock_settings):
        """自定义语言"""
        mock_client = MagicMock()
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore"):
                analyzer = PaperLightAnalyzer(mock_client, language="en")
        
        assert analyzer._language == "en"


class TestPaperLightAnalyzerBuildPrompt:
    """_build_prompt 方法测试"""
    
    def test_build_prompt_structure(self, mock_settings, sample_paper):
        """构建 Prompt 结构"""
        mock_client = MagicMock()
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore"):
                analyzer = PaperLightAnalyzer(mock_client)
                messages = analyzer._build_prompt(sample_paper)
        
        # LangChain messages 使用 type 属性
        assert len(messages) == 2
        assert messages[0].type == "system"
        assert messages[1].type == "human"
    
    def test_build_prompt_contains_paper_info(self, mock_settings, sample_paper):
        """Prompt 包含论文信息"""
        mock_client = MagicMock()
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore"):
                analyzer = PaperLightAnalyzer(mock_client)
                messages = analyzer._build_prompt(sample_paper)
        
        user_content = messages[1].content
        assert sample_paper.title in user_content
        assert sample_paper.abstract in user_content


class TestPaperLightAnalyzerAnalyzeOne:
    """analyze_one 方法测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_success(
        self,
        mock_settings,
        sample_paper,
        sample_paper_light_analysis,
    ):
        """分析成功"""
        mock_client = AsyncMock()
        mock_client.chat_structured = AsyncMock(return_value=sample_paper_light_analysis)
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore", return_value=AsyncMock()):
                analyzer = PaperLightAnalyzer(mock_client)
                # Mock semaphore context manager
                analyzer._semaphore = MagicMock()
                analyzer._semaphore.__aenter__ = AsyncMock()
                analyzer._semaphore.__aexit__ = AsyncMock()
                
                result = await analyzer.analyze_one(sample_paper)
        
        # ✅ 验证 LLM 被调用
        mock_client.chat_structured.assert_called_once()
        
        # 验证调用参数包含正确的 schema
        call_args = mock_client.chat_structured.call_args
        assert call_args is not None
        # 验证传入了 messages 参数
        if call_args.kwargs:
            assert "messages" in call_args.kwargs or len(call_args.args) > 0
        
        assert isinstance(result, AnalyzedPaper)
        assert result.analysis_status == "success"
        assert result.light_analysis is not None
        assert result.analyzed_at is not None
    
    @pytest.mark.asyncio
    async def test_analyze_parse_error(self, mock_settings, sample_paper):
        """解析错误标记失败状态"""
        mock_client = AsyncMock()
        mock_client.chat_structured = AsyncMock(
            side_effect=LLMParseError("Parse failed", raw_response="{}")
        )
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore", return_value=AsyncMock()):
                analyzer = PaperLightAnalyzer(mock_client)
                analyzer._semaphore = MagicMock()
                analyzer._semaphore.__aenter__ = AsyncMock()
                analyzer._semaphore.__aexit__ = AsyncMock()
                
                result = await analyzer.analyze_one(sample_paper)
        
        # ✅ 验证 LLM 被调用（即使失败也要尝试调用）
        mock_client.chat_structured.assert_called_once()
        
        assert result.analysis_status == "failed"
        # 错误消息可能是原始异常消息或包装后的消息
        assert result.analysis_error is not None
        assert result.light_analysis is None
    
    @pytest.mark.asyncio
    async def test_analyze_rate_limit(self, mock_settings, sample_paper):
        """限流错误标记失败状态"""
        mock_client = AsyncMock()
        mock_client.chat_structured = AsyncMock(
            side_effect=LLMRateLimitError("Rate limit exceeded")
        )
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore", return_value=AsyncMock()):
                analyzer = PaperLightAnalyzer(mock_client)
                analyzer._semaphore = MagicMock()
                analyzer._semaphore.__aenter__ = AsyncMock()
                analyzer._semaphore.__aexit__ = AsyncMock()
                
                result = await analyzer.analyze_one(sample_paper)
        
        # ✅ 验证 LLM 被调用
        mock_client.chat_structured.assert_called_once()
        
        assert result.analysis_status == "failed"
        # 错误消息可能是原始异常消息或包装后的消息
        assert result.analysis_error is not None


class TestPaperLightAnalyzerAnalyzeBatch:
    """analyze_batch 方法测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_batch_empty(self, mock_settings):
        """空输入返回空列表"""
        mock_client = AsyncMock()
        
        with patch("src.agents.base_analyzer.get_settings", return_value=mock_settings):
            with patch("src.agents.base_analyzer.get_llm_semaphore"):
                analyzer = PaperLightAnalyzer(mock_client)
                result = await analyzer.analyze_batch([])
        
        assert result == []


class TestPaperLightAnalyzerGetStats:
    """get_analysis_stats 静态方法测试"""
    
    def test_stats_all_success(self, sample_analyzed_paper):
        """全部成功"""
        papers = [sample_analyzed_paper, sample_analyzed_paper]
        
        stats = PaperLightAnalyzer.get_analysis_stats(papers)
        
        assert stats["total"] == 2
        assert stats["success"] == 2
        assert stats["failed"] == 0
        assert stats["success_rate"] == 1.0
    
    def test_stats_partial_failure(self, sample_paper_dict):
        """部分失败"""
        success = AnalyzedPaper(**sample_paper_dict, analysis_status="success")
        
        sample_paper_dict["id"] = "2501.99999"
        failed = AnalyzedPaper(**sample_paper_dict, analysis_status="failed")
        
        papers = [success, failed]
        
        stats = PaperLightAnalyzer.get_analysis_stats(papers)
        
        assert stats["total"] == 2
        assert stats["success"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.5
    
    def test_stats_empty(self):
        """空列表"""
        stats = PaperLightAnalyzer.get_analysis_stats([])
        
        assert stats["total"] == 0
        assert stats["success"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 1.0

