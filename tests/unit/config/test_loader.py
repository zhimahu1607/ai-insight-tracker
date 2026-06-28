"""
配置加载器测试

测试配置加载、合并、环境变量处理等功能。
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

import yaml


class TestDeepMerge:
    """_deep_merge 函数测试"""
    
    def test_simple_merge(self):
        """简单字典合并"""
        from src.config.loader import _deep_merge
        
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        
        result = _deep_merge(base, override)
        
        assert result == {"a": 1, "b": 3, "c": 4}
    
    def test_nested_merge(self):
        """嵌套字典深度合并"""
        from src.config.loader import _deep_merge
        
        base = {
            "llm": {"provider": "openai", "model": "gpt-4"},
            "arxiv": {"max_results": 100},
        }
        override = {
            "llm": {"model": "gpt-4-turbo"},
            "notification": {"language": "en"},
        }
        
        result = _deep_merge(base, override)
        
        assert result["llm"]["provider"] == "openai"  # 保留
        assert result["llm"]["model"] == "gpt-4-turbo"  # 覆盖
        assert result["arxiv"]["max_results"] == 100  # 保留
        assert result["notification"]["language"] == "en"  # 新增
    
    def test_empty_base(self):
        """空基础字典"""
        from src.config.loader import _deep_merge
        
        result = _deep_merge({}, {"a": 1})
        assert result == {"a": 1}
    
    def test_empty_override(self):
        """空覆盖字典"""
        from src.config.loader import _deep_merge
        
        result = _deep_merge({"a": 1}, {})
        assert result == {"a": 1}


class TestSetNestedValue:
    """_set_nested_value 函数测试"""
    
    def test_set_simple_path(self):
        """设置简单路径"""
        from src.config.loader import _set_nested_value
        
        data = {}
        _set_nested_value(data, "key", "value", only_if_empty=False)
        
        assert data == {"key": "value"}
    
    def test_set_nested_path(self):
        """设置嵌套路径"""
        from src.config.loader import _set_nested_value
        
        data = {}
        _set_nested_value(data, "llm.api_key", "secret", only_if_empty=False)
        
        assert data == {"llm": {"api_key": "secret"}}
    
    def test_only_if_empty_true(self):
        """only_if_empty=True 时不覆盖已有值"""
        from src.config.loader import _set_nested_value
        
        data = {"key": "existing"}
        _set_nested_value(data, "key", "new", only_if_empty=True)
        
        assert data["key"] == "existing"
    
    def test_only_if_empty_false(self):
        """only_if_empty=False 时覆盖已有值"""
        from src.config.loader import _set_nested_value
        
        data = {"key": "existing"}
        _set_nested_value(data, "key", "new", only_if_empty=False)
        
        assert data["key"] == "new"
    
    def test_only_if_empty_with_empty_string(self):
        """空字符串视为空值"""
        from src.config.loader import _set_nested_value
        
        data = {"key": ""}
        _set_nested_value(data, "key", "new", only_if_empty=True)
        
        assert data["key"] == "new"


class TestParseCategories:
    """_parse_categories 函数测试"""
    
    def test_simple_categories(self):
        """简单分类列表"""
        from src.config.loader import _parse_categories
        
        result = _parse_categories("cs.AI,cs.CL,cs.CV")
        
        assert result == ["cs.AI", "cs.CL", "cs.CV"]
    
    def test_categories_with_spaces(self):
        """带空格的分类"""
        from src.config.loader import _parse_categories
        
        result = _parse_categories("cs.AI, cs.CL, cs.CV")
        
        assert result == ["cs.AI", "cs.CL", "cs.CV"]
    
    def test_categories_with_extra_spaces(self):
        """首尾空格"""
        from src.config.loader import _parse_categories
        
        result = _parse_categories(" cs.AI , cs.CL ")
        
        assert result == ["cs.AI", "cs.CL"]
    
    def test_single_category(self):
        """单个分类"""
        from src.config.loader import _parse_categories
        
        result = _parse_categories("cs.AI")
        
        assert result == ["cs.AI"]
    
    def test_empty_string(self):
        """空字符串"""
        from src.config.loader import _parse_categories
        
        result = _parse_categories("")
        
        assert result == []


class TestConvertEnvValue:
    """_convert_env_value 函数测试"""
    
    def test_convert_categories(self):
        """转换分类列表"""
        from src.config.loader import _convert_env_value
        
        result = _convert_env_value("arxiv.categories", "cs.AI,cs.CL")
        
        assert result == ["cs.AI", "cs.CL"]
    
    def test_convert_int(self):
        """转换整数"""
        from src.config.loader import _convert_env_value
        
        result = _convert_env_value("arxiv.max_results", "200")
        
        assert result == 200
        assert isinstance(result, int)
    
    def test_convert_float(self):
        """转换浮点数"""
        from src.config.loader import _convert_env_value
        
        result = _convert_env_value("arxiv.request_delay", "5.0")
        
        assert result == 5.0
        assert isinstance(result, float)
    
    def test_convert_string(self):
        """保持字符串"""
        from src.config.loader import _convert_env_value
        
        result = _convert_env_value("llm.provider", "openai")
        
        assert result == "openai"
        assert isinstance(result, str)

    def test_convert_github_trending_bool(self):
        """转换 GitHub Trending 布尔配置"""
        from src.config.loader import _convert_env_value

        assert _convert_env_value("news.github_trending_enabled", "true") is True
        assert _convert_env_value("news.github_trending_enabled", "0") is False

    def test_convert_github_trending_numbers(self):
        """转换 GitHub Trending 数值配置"""
        from src.config.loader import _convert_env_value

        assert _convert_env_value("news.github_trending_limit", "25") == 25
        assert _convert_env_value("news.github_trending_min_stars", "1000") == 1000
        assert _convert_env_value("news.github_trending_readme_max_chars", "8000") == 8000
        assert _convert_env_value("news.github_trending_weight", "0.9") == 0.9


class TestLoadYamlConfig:
    """_load_yaml_config 函数测试"""
    
    def test_load_existing_file(self, temp_config_dir):
        """加载存在的配置文件"""
        from src.config.loader import _load_yaml_config
        
        config_file = temp_config_dir / "settings.yaml"
        config_file.write_text("llm:\n  provider: openai\n")
        
        result = _load_yaml_config(config_file)
        
        assert result == {"llm": {"provider": "openai"}}
    
    def test_load_nonexistent_file(self, temp_config_dir):
        """加载不存在的文件返回空字典"""
        from src.config.loader import _load_yaml_config
        
        config_file = temp_config_dir / "nonexistent.yaml"
        
        result = _load_yaml_config(config_file)
        
        assert result == {}
    
    def test_load_empty_file(self, temp_config_dir):
        """加载空文件返回空字典"""
        from src.config.loader import _load_yaml_config
        
        config_file = temp_config_dir / "empty.yaml"
        config_file.write_text("")
        
        result = _load_yaml_config(config_file)
        
        assert result == {}


class TestLoadEnvConfig:
    """_load_env_config 函数测试"""
    
    def test_load_env_variables(self):
        """从环境变量加载配置"""
        from src.config.loader import _load_env_config
        
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "deepseek",
            "LLM_MODEL": "deepseek-v4-pro",
            "LLM_API_KEY": "test-key",
        }):
            result = _load_env_config()
        
        assert result["llm"]["provider"] == "deepseek"
        assert result["llm"]["model"] == "deepseek-v4-pro"
        assert result["llm"]["api_key"] == "test-key"
    
    def test_load_categories_env(self):
        """加载 CATEGORIES 环境变量"""
        from src.config.loader import _load_env_config
        
        with patch.dict(os.environ, {"CATEGORIES": "cs.AI,cs.CL"}, clear=False):
            result = _load_env_config()
        
        assert result["arxiv"]["categories"] == ["cs.AI", "cs.CL"]

    def test_load_github_trending_env(self):
        """加载 GitHub Trending 环境变量"""
        from src.config.loader import _load_env_config

        with patch.dict(os.environ, {
            "GITHUB_TRENDING_ENABLED": "true",
            "GITHUB_TRENDING_SINCE": "weekly",
            "GITHUB_TRENDING_LANGUAGE": "python",
            "GITHUB_TRENDING_LIMIT": "25",
            "GITHUB_TRENDING_MIN_STARS": "1000",
            "GITHUB_TRENDING_WEIGHT": "0.9",
            "GITHUB_TRENDING_README_MAX_CHARS": "8000",
        }, clear=False):
            result = _load_env_config()

        assert result["news"]["github_trending_enabled"] is True
        assert result["news"]["github_trending_since"] == "weekly"
        assert result["news"]["github_trending_language"] == "python"
        assert result["news"]["github_trending_limit"] == 25
        assert result["news"]["github_trending_min_stars"] == 1000
        assert result["news"]["github_trending_weight"] == 0.9
        assert result["news"]["github_trending_readme_max_chars"] == 8000
    
    def test_no_env_variables(self):
        """无相关环境变量时返回空字典"""
        from src.config.loader import _load_env_config
        
        # 清除所有相关环境变量
        env_vars_to_clear = [
            "LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY",
            "CATEGORIES", "FEISHU_WEBHOOK_URL",
        ]
        
        with patch.dict(os.environ, {}, clear=True):
            result = _load_env_config()
        
        # 结果应该是空或只包含空字典
        assert result == {} or all(not v for v in result.values())


class TestLoadSettings:
    """load_settings 函数测试"""
    
    def test_load_from_yaml(self, temp_config_dir, mock_settings_dict):
        """从 YAML 文件加载"""
        from src.config.loader import load_settings
        
        config_file = temp_config_dir / "settings.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(mock_settings_dict, f)
        
        settings = load_settings(config_path=config_file)
        
        assert settings.llm.provider == "deepseek"
        assert settings.llm.model == "deepseek-v4-pro"
    
    def test_load_without_validation(self, temp_config_dir):
        """加载但不验证"""
        from src.config.loader import load_settings_without_validation
        
        config_file = temp_config_dir / "settings.yaml"
        config_file.write_text("llm:\n  provider: ''\n")
        
        # 不应该抛出异常
        settings = load_settings_without_validation(config_path=config_file)
        
        assert settings.llm.provider == ""
    
    def test_validation_fails(self, temp_config_dir):
        """验证失败时抛出异常"""
        from src.config.loader import load_settings
        
        config_file = temp_config_dir / "settings.yaml"
        config_file.write_text("llm:\n  provider: ''\n")
        
        with pytest.raises(ValueError):
            load_settings(config_path=config_file)
    
    def test_priority_yaml_over_env(self, temp_config_dir):
        """YAML 优先级高于环境变量"""
        from src.config.loader import load_settings
        
        config_file = temp_config_dir / "settings.yaml"
        config_data = {
            "llm": {
                "provider": "yaml-provider",
                "model": "yaml-model",
                "api_key": "yaml-key",
            }
        }
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)
        
        with patch.dict(os.environ, {"LLM_PROVIDER": "env-provider"}):
            settings = load_settings(config_path=config_file)
        
        # YAML 应该覆盖环境变量
        assert settings.llm.provider == "yaml-provider"


class TestReloadSettings:
    """reload_settings 函数测试"""
    
    def test_reload_clears_cache(self, temp_config_dir, mock_settings_dict):
        """重新加载清除缓存"""
        from src.config.loader import load_settings, get_settings, reload_settings
        
        config_file = temp_config_dir / "settings.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(mock_settings_dict, f)
        
        with patch("src.config.loader._find_config_file", return_value=config_file):
            # 第一次加载
            settings1 = get_settings()
            
            # 修改配置
            mock_settings_dict["llm"]["model"] = "new-model"
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(mock_settings_dict, f)
            
            # 重新加载
            settings2 = reload_settings()
            
            assert settings2.llm.model == "new-model"

