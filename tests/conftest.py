"""
Pytest 全局配置和 Fixtures

提供测试所需的共享 fixtures 和配置。
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============================================================
# Pytest 配置
# ============================================================

def pytest_configure(config):
    """Pytest 配置钩子"""
    # 添加自定义标记
    config.addinivalue_line("markers", "slow: 标记慢速测试")
    config.addinivalue_line("markers", "integration: 标记集成测试")


# ============================================================
# 异步测试配置
# ============================================================

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环，整个测试会话共享"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================
# 环境 Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """每个测试前重置单例"""
    # 重置配置缓存
    from src.config.loader import get_settings
    get_settings.cache_clear()
    
    # 重置 LLM 信号量
    from src.agents.shared import reset_llm_semaphore
    reset_llm_semaphore()
    
    yield


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """创建临时数据目录"""
    data_dir = tmp_path / "data"
    (data_dir / "papers").mkdir(parents=True)
    (data_dir / "news").mkdir(parents=True)
    (data_dir / "reports").mkdir(parents=True)
    (data_dir / "analysis" / "deep").mkdir(parents=True)
    return data_dir


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """创建临时配置目录"""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    return config_dir


# ============================================================
# 配置 Fixtures
# ============================================================

@pytest.fixture
def mock_settings_dict() -> dict[str, Any]:
    """Mock 配置字典"""
    return {
        "llm": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_key": "test-api-key-12345",
        },
        "arxiv": {
            "categories": ["cs.AI", "cs.CL"],
            "max_results": 50,
            "request_delay": 3.0,
            "timeout": 60.0,
        },
        "search": {
            "api": "tavily",
            "tavily_api_key": "test-tavily-key",
            "max_results": 5,
            "timeout": 30,
        },
        "analysis": {
            "max_concurrent": 5,
            "timeout": 60,
            "max_research_iterations": 3,
            "max_write_iterations": 2,
        },
        "notification": {
            "feishu_webhook_url": "https://open.feishu.cn/test-webhook",
            "language": "zh",
            "max_papers": 10,
            "max_news": 5,
            "timeout": 30,
            "max_retries": 3,
        },
        "advanced": {
            "llm_timeout": 60,
            "llm_max_retries": 3,
            "rss_hours": 24,
            "rss_max_concurrent": 20,
            "rss_timeout": 30.0,
        },
    }


@pytest.fixture
def mock_settings(mock_settings_dict: dict[str, Any], temp_config_dir: Path):
    """Mock 配置系统"""
    config_file = temp_config_dir / "settings.yaml"
    
    import yaml
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(mock_settings_dict, f)
    
    with patch("src.config.loader._find_config_file", return_value=config_file):
        from src.config.loader import load_settings
        settings = load_settings(config_path=config_file)
        yield settings


@pytest.fixture
def mock_settings_no_validation(mock_settings_dict: dict[str, Any], temp_config_dir: Path):
    """Mock 配置系统（不验证必填项）"""
    config_file = temp_config_dir / "settings.yaml"
    
    # 创建不完整的配置
    incomplete_dict = mock_settings_dict.copy()
    incomplete_dict["llm"]["api_key"] = ""
    
    import yaml
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(incomplete_dict, f)
    
    with patch("src.config.loader._find_config_file", return_value=config_file):
        from src.config.loader import load_settings_without_validation
        settings = load_settings_without_validation(config_path=config_file)
        yield settings


# ============================================================
# 数据模型 Fixtures
# ============================================================

@pytest.fixture
def sample_paper_dict() -> dict[str, Any]:
    """示例论文数据字典"""
    return {
        "id": "2501.12345",
        "title": "Test Paper: A Novel Approach to AI Testing",
        "authors": ["Alice Smith", "Bob Johnson", "Carol Williams"],
        "abstract": "This paper presents a novel approach to testing AI systems. We propose a comprehensive framework that addresses key challenges in automated testing.",
        "categories": ["cs.AI", "cs.CL", "cs.LG"],
        "primary_category": "cs.AI",
        "pdf_url": "https://arxiv.org/pdf/2501.12345.pdf",
        "abs_url": "https://arxiv.org/abs/2501.12345",
        "published": datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        "updated": datetime(2025, 1, 16, 10, 0, 0, tzinfo=timezone.utc),
        "comment": "Accepted at ICML 2025",
    }


@pytest.fixture
def sample_paper(sample_paper_dict: dict[str, Any]):
    """示例 Paper 对象"""
    from src.models import Paper
    return Paper(**sample_paper_dict)


@pytest.fixture
def sample_paper_light_analysis_dict() -> dict[str, Any]:
    """示例论文浅度分析字典"""
    return {
        "overview": "提出了一种新的 AI 测试框架",
        "motivation": "现有 AI 测试方法存在覆盖不全的问题，难以全面验证复杂 AI 系统的行为正确性。传统测试方法无法有效处理 AI 模型的非确定性和高维输入空间。",
        "method": "采用多层次测试策略和自动化生成技术，结合符号执行和模糊测试方法，设计了一套针对 AI 系统特性的测试框架。",
        "result": "在多个基准数据集上进行了广泛实验，与现有方法相比，测试覆盖率提升了 35%，错误检测率提升了 28%。",
        "conclusion": "该框架可有效提升 AI 系统的测试效率和覆盖率，为 AI 系统的质量保障提供了新的技术方案，具有重要的学术价值和应用前景。",
        "tags": ["AI Testing", "Automated Testing", "Framework"],
    }


@pytest.fixture
def sample_paper_light_analysis(sample_paper_light_analysis_dict: dict[str, Any]):
    """示例 PaperLightAnalysis 对象"""
    from src.models import PaperLightAnalysis
    return PaperLightAnalysis(**sample_paper_light_analysis_dict)


@pytest.fixture
def sample_analyzed_paper(sample_paper_dict: dict[str, Any], sample_paper_light_analysis_dict: dict[str, Any]):
    """示例 AnalyzedPaper 对象"""
    from src.models import AnalyzedPaper, PaperLightAnalysis
    
    return AnalyzedPaper(
        **sample_paper_dict,
        light_analysis=PaperLightAnalysis(**sample_paper_light_analysis_dict),
        analyzed_at=datetime.now(timezone.utc),
        analysis_status="success",
    )


@pytest.fixture
def sample_rss_source_dict() -> dict[str, Any]:
    """示例 RSS 源配置字典"""
    return {
        "name": "Hacker News",
        "url": "https://news.ycombinator.com/rss",
        "category": "tech",
        "language": "en",
        "weight": 0.9,
        "enabled": True,
    }


@pytest.fixture
def sample_rss_source(sample_rss_source_dict: dict[str, Any]):
    """示例 RSSSource 对象"""
    from src.models import RSSSource
    return RSSSource(**sample_rss_source_dict)


@pytest.fixture
def sample_news_item_dict() -> dict[str, Any]:
    """示例热点数据字典"""
    return {
        "id": "abc123def456",
        "title": "OpenAI Releases GPT-5 with Revolutionary Capabilities",
        "url": "https://example.com/news/gpt5",
        "source_name": "Hacker News",
        "source_category": "tech",
        "language": "en",
        "published": datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        "summary": "OpenAI has announced the release of GPT-5, featuring significant improvements in reasoning and multimodal capabilities.",
        "weight": 0.9,
    }


@pytest.fixture
def sample_news_item(sample_news_item_dict: dict[str, Any]):
    """示例 NewsItem 对象"""
    from src.models import NewsItem
    return NewsItem(**sample_news_item_dict)


@pytest.fixture
def sample_news_light_analysis_dict() -> dict[str, Any]:
    """示例热点浅度分析字典"""
    return {
        "summary": "OpenAI 正式发布 GPT-5，这是其迄今为止最强大的大语言模型。GPT-5 在推理能力、多模态理解和代码生成方面取得了显著突破，支持更长的上下文窗口和更精准的指令遵循。该模型已向 ChatGPT Plus 和 Enterprise 用户开放使用。",
        "category": "AI",
        "sentiment": "positive",
        "keywords": ["GPT-5", "OpenAI", "LLM", "多模态"],
    }


@pytest.fixture
def sample_news_light_analysis(sample_news_light_analysis_dict: dict[str, Any]):
    """示例 NewsLightAnalysis 对象"""
    from src.models import NewsLightAnalysis
    return NewsLightAnalysis(**sample_news_light_analysis_dict)


@pytest.fixture
def sample_analyzed_news(sample_news_item_dict: dict[str, Any], sample_news_light_analysis_dict: dict[str, Any]):
    """示例 AnalyzedNews 对象"""
    from src.models import AnalyzedNews, NewsLightAnalysis
    
    return AnalyzedNews(
        **sample_news_item_dict,
        light_analysis=NewsLightAnalysis(**sample_news_light_analysis_dict),
        analyzed_at=datetime.now(timezone.utc),
        analysis_status="success",
    )


@pytest.fixture
def sample_daily_stats_dict() -> dict[str, Any]:
    """示例每日统计字典"""
    return {
        "total_papers": 50,
        "papers_by_category": {"cs.AI": 20, "cs.CL": 15, "cs.LG": 15},
        "total_news": 10,
        "news_by_category": {"AI": 5, "LLM": 3, "开源": 2},
        "top_keywords": ["LLM", "GPT", "Transformer", "AI Agent", "RAG"],
    }


@pytest.fixture
def sample_daily_stats(sample_daily_stats_dict: dict[str, Any]):
    """示例 DailyStats 对象"""
    from src.models import DailyStats
    return DailyStats(**sample_daily_stats_dict)


@pytest.fixture
def sample_daily_report(
    sample_daily_stats,
):
    """示例 DailyReport 对象"""
    from src.models import DailyReport
    
    return DailyReport(
        date="2025-01-15",
        summary="今日共收录 50 篇论文，10 条热点资讯。热门领域：cs.AI、cs.CL。",
        category_summaries={"cs.AI": "AI 领域研究进展"},
        news_summary="行业新闻汇总",
        stats=sample_daily_stats,
        generated_at=datetime.now(timezone.utc),
    )


# ============================================================
# LLM Mock Fixtures
# ============================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM 客户端"""
    with patch("src.llm.client.LLMClient") as mock_class:
        mock_instance = AsyncMock()
        mock_instance.chat = AsyncMock(return_value="Test response")
        mock_instance.chat_structured = AsyncMock()
        mock_instance.close = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.provider = "deepseek"
        mock_instance.model = "deepseek-chat"
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_langchain_llm():
    """Mock LangChain ChatOpenAI"""
    with patch("src.llm.client.ChatOpenAI") as mock_class:
        mock_instance = MagicMock()
        mock_instance.ainvoke = AsyncMock()
        mock_instance.astream = AsyncMock()
        mock_instance.with_structured_output = MagicMock(return_value=mock_instance)
        mock_instance.bind = MagicMock(return_value=mock_instance)
        mock_class.return_value = mock_instance
        yield mock_instance


# ============================================================
# HTTP Mock Fixtures
# ============================================================

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession"""
    with patch("aiohttp.ClientSession") as mock_class:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_class.return_value = mock_session
        yield mock_session


# ============================================================
# 测试数据文件 Fixtures
# ============================================================

@pytest.fixture
def arxiv_atom_response() -> str:
    """arXiv API Atom XML 响应样本"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>arXiv Query</title>
  <id>http://arxiv.org/api/query</id>
  <entry>
    <id>http://arxiv.org/abs/2501.12345v1</id>
    <title>Test Paper: A Novel Approach</title>
    <summary>This is a test abstract for the paper.</summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Johnson</name></author>
    <published>2025-01-15T00:00:00Z</published>
    <updated>2025-01-16T00:00:00Z</updated>
    <link href="http://arxiv.org/abs/2501.12345v1" rel="alternate" type="text/html"/>
    <link href="http://arxiv.org/pdf/2501.12345v1" title="pdf" type="application/pdf"/>
    <category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.AI"/>
  </entry>
</feed>'''


@pytest.fixture
def rss_feed_content() -> str:
    """RSS Feed XML 样本"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>Test RSS Feed</description>
    <item>
      <title>Test News Item</title>
      <link>https://example.com/news/1</link>
      <description>This is a test news item description.</description>
      <pubDate>Wed, 15 Jan 2025 10:30:00 +0000</pubDate>
    </item>
    <item>
      <title>Another News Item</title>
      <link>https://example.com/news/2</link>
      <description>Another test description.</description>
      <pubDate>Wed, 15 Jan 2025 09:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>'''


@pytest.fixture
def sample_papers_jsonl(sample_paper_dict: dict[str, Any], temp_data_dir: Path) -> Path:
    """创建示例论文 JSONL 文件"""
    from src.models import Paper
    
    file_path = temp_data_dir / "papers" / "2025-01-15.jsonl"
    paper = Paper(**sample_paper_dict)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(paper.model_dump_json() + "\n")
    
    return file_path


@pytest.fixture
def sample_news_jsonl(sample_news_item_dict: dict[str, Any], temp_data_dir: Path) -> Path:
    """创建示例热点 JSONL 文件"""
    from src.models import NewsItem
    
    file_path = temp_data_dir / "news" / "2025-01-15.jsonl"
    news = NewsItem(**sample_news_item_dict)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(news.model_dump_json() + "\n")
    
    return file_path

