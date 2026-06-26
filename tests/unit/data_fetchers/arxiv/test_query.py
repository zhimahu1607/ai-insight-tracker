"""
arXiv 查询构建器测试

测试 build_category_query, build_id_query 等函数。
"""

import pytest
from urllib.parse import urlparse, parse_qs

from src.data_fetchers.arxiv.query import (
    ARXIV_API_ENDPOINT,
    build_category_query,
    build_single_category_query,
    build_id_query,
)


class TestBuildCategoryQuery:
    """build_category_query 函数测试"""
    
    def test_single_category(self):
        """单分类查询"""
        from urllib.parse import unquote
        
        url = build_category_query(["cs.AI"])
        decoded_url = unquote(url)
        
        assert ARXIV_API_ENDPOINT in url
        assert "cat:cs.AI" in decoded_url
    
    def test_multiple_categories(self):
        """多分类查询"""
        from urllib.parse import unquote
        
        url = build_category_query(["cs.AI", "cs.CL", "cs.CV"])
        decoded_url = unquote(url)
        
        assert "cat:cs.AI" in decoded_url
        assert "cat:cs.CL" in decoded_url
        assert "cat:cs.CV" in decoded_url
        assert "OR" in decoded_url
    
    def test_max_results_param(self):
        """max_results 参数"""
        url = build_category_query(["cs.AI"], max_results=50)
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params["max_results"] == ["50"]
    
    def test_start_param(self):
        """start 参数"""
        url = build_category_query(["cs.AI"], start=100)
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params["start"] == ["100"]
    
    def test_sort_params(self):
        """排序参数"""
        url = build_category_query(
            ["cs.AI"],
            sort_by="lastUpdatedDate",
            sort_order="ascending",
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params["sortBy"] == ["lastUpdatedDate"]
        assert params["sortOrder"] == ["ascending"]
    
    def test_default_sort(self):
        """默认排序"""
        url = build_category_query(["cs.AI"])
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params["sortBy"] == ["lastUpdatedDate"]
        assert params["sortOrder"] == ["descending"]


class TestBuildSingleCategoryQuery:
    """build_single_category_query 函数测试"""
    
    def test_single_category(self):
        """单分类便捷方法"""
        from urllib.parse import unquote
        
        url = build_single_category_query("cs.AI")
        decoded_url = unquote(url)
        
        assert "cat:cs.AI" in decoded_url
        assert "OR" not in decoded_url
    
    def test_with_params(self):
        """带参数"""
        url = build_single_category_query("cs.AI", max_results=25, start=50)
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params["max_results"] == ["25"]
        assert params["start"] == ["50"]


class TestBuildIdQuery:
    """build_id_query 函数测试"""
    
    def test_single_id(self):
        """单 ID 查询"""
        url = build_id_query(["2501.12345"])
        
        assert ARXIV_API_ENDPOINT in url
        assert "id_list=2501.12345" in url
    
    def test_multiple_ids(self):
        """多 ID 查询"""
        url = build_id_query(["2501.12345", "2501.12346", "2501.12347"])
        
        assert "2501.12345" in url
        assert "2501.12346" in url
        assert "2501.12347" in url
    
    def test_ids_comma_separated(self):
        """ID 逗号分隔"""
        url = build_id_query(["2501.12345", "2501.12346"])
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params["id_list"] == ["2501.12345,2501.12346"]
