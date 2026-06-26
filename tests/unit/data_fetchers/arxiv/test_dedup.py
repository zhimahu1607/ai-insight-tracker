"""
arXiv 论文去重测试

测试 load_all_historical_ids, dedup_papers 等函数。
"""

import json
import pytest
from pathlib import Path

from src.data_fetchers.arxiv.dedup import (
    DedupStatus,
    load_all_historical_ids,
    dedup_papers,
    extract_paper_ids_from_json,
)
from src.models import Paper


class TestLoadAllHistoricalIds:
    """load_all_historical_ids 函数测试"""
    
    def test_empty_directory(self, temp_data_dir):
        """空目录返回空集合"""
        papers_dir = temp_data_dir / "papers"
        # 删除所有文件
        for f in papers_dir.glob("*"):
            f.unlink()
        
        result = load_all_historical_ids(papers_dir)
        
        assert result == set()
    
    def test_nonexistent_directory(self, tmp_path):
        """不存在的目录返回空集合"""
        nonexistent = tmp_path / "nonexistent"
        
        result = load_all_historical_ids(nonexistent)
        
        assert result == set()
    
    def test_load_from_files(self, temp_data_dir):
        """从 JSON 文件加载 ID"""
        papers_dir = temp_data_dir / "papers"
        
        # 创建测试文件
        file1 = papers_dir / "2025-01-15.json"
        with open(file1, "w") as f:
            json.dump([{"id": "2501.12345"}, {"id": "2501.12346"}], f)
        
        file2 = papers_dir / "2025-01-16.json"
        with open(file2, "w") as f:
            json.dump([{"id": "2501.12347"}], f)
        
        result = load_all_historical_ids(papers_dir)
        
        assert result == {"2501.12345", "2501.12346", "2501.12347"}
    
    def test_skip_invalid_json(self, temp_data_dir):
        """跳过无效 JSON 文件"""
        papers_dir = temp_data_dir / "papers"
        
        file = papers_dir / "2025-01-15.json"
        file.write_text('invalid json')
        
        # 还要创建一个有效文件确保能正常加载
        file2 = papers_dir / "2025-01-16.json"
        with open(file2, "w") as f:
            json.dump([{"id": "2501.12346"}], f)

        result = load_all_historical_ids(papers_dir)
        
        assert result == {"2501.12346"}
    
    def test_skip_entries_without_id(self, temp_data_dir):
        """跳过没有 id 字段的条目"""
        papers_dir = temp_data_dir / "papers"
        
        file = papers_dir / "2025-01-15.json"
        with open(file, "w") as f:
            json.dump([{"id": "2501.12345"}, {"title": "no id"}], f)
        
        result = load_all_historical_ids(papers_dir)
        
        assert result == {"2501.12345"}


class TestDedupPapers:
    """dedup_papers 函数测试"""
    
    def test_all_new_papers(self, sample_paper):
        """全部为新论文"""
        papers = [sample_paper]
        historical_ids = set()
        
        result, status = dedup_papers(papers, historical_ids)
        
        assert status == DedupStatus.HAS_NEW_CONTENT
        assert len(result) == 1
        assert result[0].id == sample_paper.id
    
    def test_all_duplicates(self, sample_paper):
        """全部为重复论文"""
        papers = [sample_paper]
        historical_ids = {sample_paper.id}
        
        result, status = dedup_papers(papers, historical_ids)
        
        assert status == DedupStatus.NO_NEW_CONTENT
        assert len(result) == 0
    
    def test_partial_duplicates(self, sample_paper_dict):
        """部分重复"""
        paper1 = Paper(**sample_paper_dict)
        
        sample_paper_dict["id"] = "2501.99999"
        paper2 = Paper(**sample_paper_dict)
        
        papers = [paper1, paper2]
        historical_ids = {paper1.id}  # paper1 是重复的
        
        result, status = dedup_papers(papers, historical_ids)
        
        assert status == DedupStatus.HAS_NEW_CONTENT
        assert len(result) == 1
        assert result[0].id == "2501.99999"
    
    def test_empty_input(self):
        """空输入"""
        result, status = dedup_papers([], set())
        
        assert status == DedupStatus.NO_NEW_CONTENT
        assert len(result) == 0


class TestExtractPaperIdsFromJson:
    """extract_paper_ids_from_json 函数测试"""
    
    def test_extract_ids(self, temp_data_dir):
        """提取 ID"""
        file = temp_data_dir / "papers" / "test.json"
        with open(file, "w") as f:
            json.dump([{"id": "2501.12345"}, {"id": "2501.12346"}], f)
        
        result = extract_paper_ids_from_json(file)
        
        assert result == {"2501.12345", "2501.12346"}
    
    def test_nonexistent_file(self, temp_data_dir):
        """不存在的文件返回空集合"""
        file = temp_data_dir / "papers" / "nonexistent.json"
        
        result = extract_paper_ids_from_json(file)
        
        assert result == set()
    
    def test_empty_file(self, temp_data_dir):
        """空文件返回空集合"""
        file = temp_data_dir / "papers" / "empty.json"
        file.write_text("")
        
        result = extract_paper_ids_from_json(file)
        
        assert result == set()

