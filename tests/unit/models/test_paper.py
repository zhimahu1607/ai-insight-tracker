"""
论文数据模型测试

测试 Paper, PaperLightAnalysis, AnalyzedPaper 模型。
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.models import Paper, PaperLightAnalysis, AnalyzedPaper


class TestPaper:
    """Paper 模型测试"""
    
    def test_valid_paper(self, sample_paper_dict):
        """创建有效的 Paper 对象"""
        paper = Paper(**sample_paper_dict)
        
        assert paper.id == "2501.12345"
        assert paper.title == "Test Paper: A Novel Approach to AI Testing"
        assert len(paper.authors) == 3
        assert paper.primary_category == "cs.AI"
        assert str(paper.pdf_url) == "https://arxiv.org/pdf/2501.12345.pdf"
    
    def test_required_fields(self):
        """必填字段缺失时应该失败"""
        with pytest.raises(ValidationError):
            Paper(
                id="2501.12345",
                title="Test",
                # 缺少其他必填字段
            )
    
    def test_invalid_url(self, sample_paper_dict):
        """无效 URL 应该失败"""
        sample_paper_dict["pdf_url"] = "not-a-valid-url"
        
        with pytest.raises(ValidationError):
            Paper(**sample_paper_dict)
    
    def test_optional_fields(self, sample_paper_dict):
        """可选字段可以为 None"""
        sample_paper_dict["updated"] = None
        sample_paper_dict["comment"] = None
        
        paper = Paper(**sample_paper_dict)
        
        assert paper.updated is None
        assert paper.comment is None
    
    def test_serialization(self, sample_paper):
        """序列化和反序列化"""
        json_str = sample_paper.model_dump_json()
        restored = Paper.model_validate_json(json_str)
        
        assert restored.id == sample_paper.id
        assert restored.title == sample_paper.title


class TestPaperLightAnalysis:
    """PaperLightAnalysis 模型测试"""
    
    def test_valid_analysis(self, sample_paper_light_analysis_dict):
        """创建有效的 PaperLightAnalysis 对象"""
        analysis = PaperLightAnalysis(**sample_paper_light_analysis_dict)
        
        assert analysis.overview == "提出了一种新的 AI 测试框架"
        assert len(analysis.tags) == 3
    
    def test_tags_validation(self, sample_paper_light_analysis_dict):
        """tags 数量验证"""
        # 少于 3 个
        sample_paper_light_analysis_dict["tags"] = ["tag1"]
        
        with pytest.raises(ValidationError):
            PaperLightAnalysis(**sample_paper_light_analysis_dict)


class TestAnalyzedPaper:
    """AnalyzedPaper 模型测试"""
    
    def test_valid_analyzed_paper(self, sample_analyzed_paper):
        """创建有效的 AnalyzedPaper 对象"""
        assert sample_analyzed_paper.id == "2501.12345"
        assert sample_analyzed_paper.analysis_status == "success"
        assert sample_analyzed_paper.light_analysis is not None
        assert sample_analyzed_paper.analyzed_at is not None
    
    def test_is_analyzed_property_success(self, sample_analyzed_paper):
        """分析成功时 is_analyzed 为 True"""
        assert sample_analyzed_paper.is_analyzed is True
    
    def test_is_analyzed_property_pending(self, sample_paper_dict):
        """待分析时 is_analyzed 为 False"""
        paper = AnalyzedPaper(
            **sample_paper_dict,
            analysis_status="pending",
        )
        
        assert paper.is_analyzed is False
    
    def test_is_analyzed_property_failed(self, sample_paper_dict):
        """分析失败时 is_analyzed 为 False"""
        paper = AnalyzedPaper(
            **sample_paper_dict,
            analysis_status="failed",
            analysis_error="LLM timeout",
        )
        
        assert paper.is_analyzed is False
    
    def test_is_analyzed_no_result(self, sample_paper_dict):
        """状态成功但无分析结果时 is_analyzed 为 False"""
        paper = AnalyzedPaper(
            **sample_paper_dict,
            analysis_status="success",
            light_analysis=None,
        )
        
        assert paper.is_analyzed is False
    
    def test_status_transitions(self, sample_paper_dict):
        """分析状态值验证"""
        # pending
        paper = AnalyzedPaper(**sample_paper_dict, analysis_status="pending")
        assert paper.analysis_status == "pending"
        
        # success
        paper = AnalyzedPaper(**sample_paper_dict, analysis_status="success")
        assert paper.analysis_status == "success"
        
        # failed
        paper = AnalyzedPaper(**sample_paper_dict, analysis_status="failed")
        assert paper.analysis_status == "failed"
    
    def test_invalid_status(self, sample_paper_dict):
        """无效的分析状态应该失败"""
        with pytest.raises(ValidationError):
            AnalyzedPaper(**sample_paper_dict, analysis_status="invalid")
    
    def test_serialization(self, sample_analyzed_paper):
        """序列化和反序列化"""
        json_str = sample_analyzed_paper.model_dump_json()
        restored = AnalyzedPaper.model_validate_json(json_str)
        
        assert restored.id == sample_analyzed_paper.id
        assert restored.is_analyzed == sample_analyzed_paper.is_analyzed

