"""
日报生成器测试

测试 DailyReportGenerator 类。
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.generators.daily_report_generator import DailyReportGenerator
from src.models import (
    AnalyzedPaper,
    AnalyzedNews,
    PaperLightAnalysis,
    NewsLightAnalysis,
    DailyStats,
    DailyReport,
)


class TestDailyReportGeneratorInit:
    """DailyReportGenerator 初始化测试"""
    
    def test_init_default(self):
        """默认初始化"""
        generator = DailyReportGenerator()
        
        assert generator._use_llm_summary is True
    
    def test_init_no_llm(self):
        """禁用 LLM 总结"""
        generator = DailyReportGenerator(use_llm_summary=False)
        
        assert generator._use_llm_summary is False
    
    def test_init_custom_data_dir(self, temp_data_dir):
        """自定义数据目录"""
        generator = DailyReportGenerator(data_dir=temp_data_dir)
        
        assert generator.DATA_DIR == temp_data_dir
        assert generator.REPORTS_DIR == temp_data_dir / "reports"


class TestDailyReportGeneratorSortPapers:
    """_sort_papers 方法测试"""
    
    def test_sort_by_status_and_time(self, sample_paper_dict, sample_paper_light_analysis_dict):
        """按状态和发布时间排序"""
        from datetime import datetime, timezone
        
        generator = DailyReportGenerator()
        
        # 成功，较新发布
        sample_paper_dict["published"] = datetime(2025, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
        newer = AnalyzedPaper(
            **sample_paper_dict,
            light_analysis=PaperLightAnalysis(**sample_paper_light_analysis_dict),
            analysis_status="success",
        )
        
        # 成功，较旧发布
        sample_paper_dict["id"] = "2501.00001"
        sample_paper_dict["published"] = datetime(2025, 1, 14, 12, 0, 0, tzinfo=timezone.utc)
        older = AnalyzedPaper(
            **sample_paper_dict,
            light_analysis=PaperLightAnalysis(**sample_paper_light_analysis_dict),
            analysis_status="success",
        )
        
        # 失败
        sample_paper_dict["id"] = "2501.00002"
        sample_paper_dict["published"] = datetime(2025, 1, 17, 12, 0, 0, tzinfo=timezone.utc)
        failed = AnalyzedPaper(
            **sample_paper_dict,
            analysis_status="failed",
        )
        
        papers = [failed, older, newer]
        result = generator._sort_papers(papers)
        
        # 成功的在前，按发布时间降序（较新的在前）
        assert result[0].id == "2501.12345"  # newer (成功，最新)
        assert result[1].id == "2501.00001"  # older (成功，较旧)
        assert result[2].id == "2501.00002"  # failed (失败，排最后)


class TestDailyReportGeneratorSortNews:
    """_sort_news 方法测试"""
    
    def test_sort_by_weight_and_time(self, sample_news_item_dict, sample_news_light_analysis_dict):
        """按权重和发布时间排序"""
        generator = DailyReportGenerator()
        
        # 高权重
        sample_news_item_dict["weight"] = 0.9
        high = AnalyzedNews(
            **sample_news_item_dict,
            light_analysis=NewsLightAnalysis(**sample_news_light_analysis_dict),
            analysis_status="success",
        )
        
        # 低权重
        sample_news_item_dict["id"] = "low123"
        sample_news_item_dict["weight"] = 0.3
        low = AnalyzedNews(
            **sample_news_item_dict,
            light_analysis=NewsLightAnalysis(**sample_news_light_analysis_dict),
            analysis_status="success",
        )
        
        news = [low, high]
        result = generator._sort_news(news)
        
        assert result[0].id == "abc123def456"  # high weight
        assert result[1].id == "low123"  # low weight


class TestDailyReportGeneratorComputeStats:
    """_compute_stats 方法测试"""
    
    def test_compute_stats(
        self,
        sample_paper_dict,
        sample_news_item_dict,
        sample_paper_light_analysis_dict,
        sample_news_light_analysis_dict,
    ):
        """计算统计信息"""
        generator = DailyReportGenerator()
        
        # 创建论文
        paper = AnalyzedPaper(
            **sample_paper_dict,
            light_analysis=PaperLightAnalysis(**sample_paper_light_analysis_dict),
            analysis_status="success",
        )
        
        # 创建热点
        news = AnalyzedNews(
            **sample_news_item_dict,
            light_analysis=NewsLightAnalysis(**sample_news_light_analysis_dict),
            analysis_status="success",
        )
        
        stats = generator._compute_stats([paper], [news])
        
        assert stats.total_papers == 1
        assert stats.total_news == 1
        assert "cs.AI" in stats.papers_by_category
        assert len(stats.top_keywords) > 0


class TestDailyReportGeneratorTemplateSummary:
    """_generate_template_summary 方法测试"""
    
    def test_template_summary(self, sample_daily_stats):
        """生成模板总结"""
        generator = DailyReportGenerator()
        
        summary = generator._generate_template_summary(sample_daily_stats)
        
        assert "50 篇论文" in summary
        assert "10 条热点" in summary


class TestDailyReportGeneratorGenerate:
    """generate 方法测试"""
    
    @pytest.mark.asyncio
    async def test_generate_with_template(
        self,
        sample_analyzed_paper,
        sample_analyzed_news,
    ):
        """使用模板生成"""
        generator = DailyReportGenerator(use_llm_summary=False)
        
        report = await generator.generate(
            [sample_analyzed_paper],
            [sample_analyzed_news],
            date="2025-01-15",
        )
        
        assert isinstance(report, DailyReport)
        assert report.date == "2025-01-15"
        assert report.paper_count == 1
        assert report.news_count == 1
        assert report.generated_at is not None
    
    @pytest.mark.asyncio
    async def test_generate_empty(self):
        """空数据生成"""
        generator = DailyReportGenerator(use_llm_summary=False)
        
        report = await generator.generate([], [], date="2025-01-15")
        
        assert report.paper_count == 0
        assert report.news_count == 0


class TestDailyReportGeneratorSave:
    """save 方法测试"""
    
    @pytest.mark.asyncio
    async def test_save_report(self, temp_data_dir, sample_daily_report):
        """保存日报"""
        generator = DailyReportGenerator(data_dir=temp_data_dir)
        
        file_path = await generator.save(sample_daily_report)
        
        assert file_path.exists()
        assert file_path.name == "2025-01-15.json"
        
        # 验证内容
        content = json.loads(file_path.read_text(encoding="utf-8"))
        assert content["date"] == "2025-01-15"
    
    @pytest.mark.asyncio
    async def test_update_file_list(self, temp_data_dir, sample_daily_report):
        """更新文件索引"""
        generator = DailyReportGenerator(data_dir=temp_data_dir)
        
        await generator.save(sample_daily_report)
        
        # 检查文件索引
        file_list_path = temp_data_dir / "file-list.json"
        assert file_list_path.exists()
        
        file_list = json.loads(file_list_path.read_text(encoding="utf-8"))
        assert "2025-01-15.json" in file_list.get("reports", [])

