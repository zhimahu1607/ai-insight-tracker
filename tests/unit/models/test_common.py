"""
共享类型定义测试

测试 Tags 和 Keywords 类型的验证逻辑。
"""

import pytest
from pydantic import BaseModel, ValidationError

from src.models.common import Tags, Keywords, validate_tags_length, validate_keywords_length


class TestValidateTagsLength:
    """validate_tags_length 函数测试"""
    
    def test_valid_3_tags(self):
        """3 个标签应该通过"""
        tags = ["tag1", "tag2", "tag3"]
        result = validate_tags_length(tags)
        assert result == tags
    
    def test_valid_5_tags(self):
        """5 个标签应该通过"""
        tags = ["tag1", "tag2", "tag3", "tag4", "tag5"]
        result = validate_tags_length(tags)
        assert result == tags
    
    def test_valid_4_tags(self):
        """4 个标签应该通过"""
        tags = ["tag1", "tag2", "tag3", "tag4"]
        result = validate_tags_length(tags)
        assert result == tags
    
    def test_too_few_tags(self):
        """少于 3 个标签应该失败"""
        with pytest.raises(ValueError, match="至少需要 3 个元素"):
            validate_tags_length(["tag1", "tag2"])
    
    def test_empty_tags(self):
        """空列表应该失败"""
        with pytest.raises(ValueError, match="至少需要 3 个元素"):
            validate_tags_length([])
    
    def test_too_many_tags(self):
        """超过 5 个标签应该失败"""
        with pytest.raises(ValueError, match="最多包含 5 个元素"):
            validate_tags_length(["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"])


class TestValidateKeywordsLength:
    """validate_keywords_length 函数测试"""
    
    def test_valid_empty(self):
        """空列表应该通过"""
        result = validate_keywords_length([])
        assert result == []
    
    def test_valid_5_keywords(self):
        """5 个关键词应该通过"""
        keywords = ["kw1", "kw2", "kw3", "kw4", "kw5"]
        result = validate_keywords_length(keywords)
        assert result == keywords
    
    def test_valid_3_keywords(self):
        """3 个关键词应该通过"""
        keywords = ["kw1", "kw2", "kw3"]
        result = validate_keywords_length(keywords)
        assert result == keywords
    
    def test_too_many_keywords(self):
        """超过 5 个关键词应该失败"""
        with pytest.raises(ValueError, match="最多包含 5 个元素"):
            validate_keywords_length(["kw1", "kw2", "kw3", "kw4", "kw5", "kw6"])


class TestTagsType:
    """Tags 类型别名测试"""
    
    def test_tags_in_model_valid(self):
        """在 Pydantic 模型中使用有效 Tags"""
        class TestModel(BaseModel):
            tags: Tags
        
        model = TestModel(tags=["tag1", "tag2", "tag3"])
        assert model.tags == ["tag1", "tag2", "tag3"]
    
    def test_tags_in_model_invalid(self):
        """在 Pydantic 模型中使用无效 Tags"""
        class TestModel(BaseModel):
            tags: Tags
        
        with pytest.raises(ValidationError):
            TestModel(tags=["tag1"])


class TestKeywordsType:
    """Keywords 类型别名测试"""
    
    def test_keywords_in_model_valid(self):
        """在 Pydantic 模型中使用有效 Keywords"""
        class TestModel(BaseModel):
            keywords: Keywords
        
        model = TestModel(keywords=["kw1", "kw2"])
        assert model.keywords == ["kw1", "kw2"]
    
    def test_keywords_in_model_empty(self):
        """在 Pydantic 模型中使用空 Keywords"""
        class TestModel(BaseModel):
            keywords: Keywords
        
        model = TestModel(keywords=[])
        assert model.keywords == []
    
    def test_keywords_in_model_invalid(self):
        """在 Pydantic 模型中使用无效 Keywords"""
        class TestModel(BaseModel):
            keywords: Keywords
        
        with pytest.raises(ValidationError):
            TestModel(keywords=["kw1", "kw2", "kw3", "kw4", "kw5", "kw6"])

