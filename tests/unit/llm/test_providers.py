"""
LLM 提供商配置测试

测试 LLMProvider, ProviderConfig, get_provider_config, get_structured_output_method 等。
基于 LangChain 实现，with_structured_output 会根据模型自动选择最佳策略。
"""

import pytest

from src.llm.providers import (
    LLMProvider,
    ProviderConfig,
    PROVIDER_CONFIGS,
    get_provider_config,
    get_structured_output_method,
)


class TestLLMProvider:
    """LLMProvider 枚举测试"""
    
    def test_all_providers_defined(self):
        """所有提供商枚举值存在"""
        expected = ["openai", "anthropic", "openrouter", "deepseek", "qwen", "gemini", "zhipu", "grok"]
        
        for provider in expected:
            assert hasattr(LLMProvider, provider.upper())
    
    def test_provider_values(self):
        """枚举值正确"""
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.DEEPSEEK.value == "deepseek"
        assert LLMProvider.ANTHROPIC.value == "anthropic"


class TestProviderConfigs:
    """PROVIDER_CONFIGS 配置表测试"""
    
    def test_all_providers_have_config(self):
        """所有提供商都有配置"""
        for provider in LLMProvider:
            assert provider.value in PROVIDER_CONFIGS
    
    def test_openai_config(self):
        """OpenAI 配置正确"""
        config = PROVIDER_CONFIGS["openai"]
        
        assert config.provider == LLMProvider.OPENAI
        assert "api.openai.com" in config.base_url
        # OpenAI 支持所有三种结构化输出方式
        assert config.supports_json_schema is True
        assert config.supports_function_calling is True
        assert config.supports_json_mode is True
    
    def test_deepseek_config(self):
        """DeepSeek 配置正确"""
        config = PROVIDER_CONFIGS["deepseek"]
        
        assert config.provider == LLMProvider.DEEPSEEK
        assert "deepseek.com" in config.base_url
        # DeepSeek 支持 function_calling 和 json_mode
        assert config.supports_function_calling is True
        assert config.supports_json_mode is True
        assert config.supports_json_schema is False
    
    def test_qwen_config(self):
        """Qwen 配置正确"""
        config = PROVIDER_CONFIGS["qwen"]
        
        assert config.provider == LLMProvider.QWEN
        assert "dashscope.aliyuncs.com" in config.base_url
    
    def test_gemini_config(self):
        """Gemini 配置正确"""
        config = PROVIDER_CONFIGS["gemini"]
        
        assert config.provider == LLMProvider.GEMINI
        assert "generativelanguage.googleapis.com" in config.base_url
    
    def test_anthropic_config(self):
        """Anthropic 配置正确"""
        config = PROVIDER_CONFIGS["anthropic"]
        
        assert config.provider == LLMProvider.ANTHROPIC
        assert "api.anthropic.com" in config.base_url
    
    def test_grok_config(self):
        """Grok 配置正确"""
        config = PROVIDER_CONFIGS["grok"]
        
        assert config.provider == LLMProvider.GROK
        assert "x.ai" in config.base_url
    
    def test_zhipu_config(self):
        """Zhipu 配置正确"""
        config = PROVIDER_CONFIGS["zhipu"]
        
        assert config.provider == LLMProvider.ZHIPU
        assert "bigmodel.cn" in config.base_url


class TestGetProviderConfig:
    """get_provider_config 函数测试"""
    
    def test_get_valid_provider(self):
        """获取有效提供商配置"""
        config = get_provider_config("openai")
        
        assert isinstance(config, ProviderConfig)
        assert config.provider == LLMProvider.OPENAI
    
    def test_get_provider_case_insensitive(self):
        """提供商名称大小写不敏感"""
        config1 = get_provider_config("OpenAI")
        config2 = get_provider_config("OPENAI")
        config3 = get_provider_config("openai")
        
        assert config1.provider == config2.provider == config3.provider
    
    def test_get_invalid_provider(self):
        """获取无效提供商抛出 ValueError"""
        with pytest.raises(ValueError, match="不支持的 LLM 提供商"):
            get_provider_config("invalid_provider")
    
    def test_error_message_includes_supported(self):
        """错误信息包含支持的提供商列表"""
        with pytest.raises(ValueError) as exc_info:
            get_provider_config("invalid")
        
        error_msg = str(exc_info.value)
        assert "openai" in error_msg
        assert "deepseek" in error_msg


class TestGetStructuredOutputMethod:
    """get_structured_output_method 函数测试"""
    
    def test_openai_gpt4o_uses_json_schema(self):
        """OpenAI GPT-4o 系列使用 json_schema"""
        assert get_structured_output_method("openai", "gpt-4o-mini") == "json_schema"
        assert get_structured_output_method("openai", "gpt-4o-2024-08-06") == "json_schema"
    
    def test_openai_gpt4_uses_function_calling(self):
        """OpenAI GPT-4 (非 4o) 使用 function_calling"""
        assert get_structured_output_method("openai", "gpt-4-turbo") == "function_calling"
        assert get_structured_output_method("openai", "gpt-3.5-turbo") == "function_calling"
    
    def test_openai_o1_uses_json_mode(self):
        """OpenAI o1 推理模型使用 json_mode"""
        assert get_structured_output_method("openai", "o1-preview") == "json_mode"
        assert get_structured_output_method("openai", "o1-mini") == "json_mode"
    
    def test_anthropic_uses_function_calling(self):
        """Anthropic Claude 使用 function_calling (唯一选项)"""
        assert get_structured_output_method("anthropic", "claude-3-5-sonnet") == "function_calling"
        assert get_structured_output_method("anthropic", "claude-3-opus") == "function_calling"
    
    def test_deepseek_chat_uses_function_calling(self):
        """DeepSeek chat 模型使用 function_calling"""
        assert get_structured_output_method("deepseek", "deepseek-chat") == "function_calling"
        assert get_structured_output_method("deepseek", "deepseek-coder") == "function_calling"
    
    def test_deepseek_reasoner_uses_json_mode(self):
        """DeepSeek reasoner 模型使用 json_mode"""
        assert get_structured_output_method("deepseek", "deepseek-reasoner") == "json_mode"
        assert get_structured_output_method("deepseek", "deepseek-r1-distill-qwen-32b") == "json_mode"
    
    def test_gemini_15_uses_json_schema(self):
        """Gemini 1.5+ 使用 json_schema"""
        assert get_structured_output_method("gemini", "gemini-1.5-pro") == "json_schema"
        assert get_structured_output_method("gemini", "gemini-2.0-flash") == "json_schema"
    
    def test_gemini_10_uses_function_calling(self):
        """Gemini 1.0 使用 function_calling"""
        assert get_structured_output_method("gemini", "gemini-1.0-pro") == "function_calling"
    
    def test_qwen_uses_function_calling(self):
        """Qwen 使用 function_calling"""
        assert get_structured_output_method("qwen", "qwen-plus") == "function_calling"
        assert get_structured_output_method("qwen", "qwen-max") == "function_calling"
    
    def test_zhipu_uses_function_calling(self):
        """智谱 GLM 使用 function_calling"""
        assert get_structured_output_method("zhipu", "glm-4") == "function_calling"
    
    def test_grok_uses_function_calling(self):
        """Grok 使用 function_calling"""
        assert get_structured_output_method("grok", "grok-beta") == "function_calling"
