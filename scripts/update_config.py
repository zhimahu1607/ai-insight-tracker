#!/usr/bin/env python3
"""
配置文件更新工具

使用 PyYAML 安全地修改 YAML 文件，避免 sed 的格式问题。
供 setup.sh 调用。

Usage:
    python scripts/update_config.py <provider> <api_key> [model]

Examples:
    python scripts/update_config.py deepseek sk-xxx
    python scripts/update_config.py openai sk-xxx gpt-4o
"""

import sys
from pathlib import Path

import yaml


# 各提供商的默认模型
DEFAULT_MODELS = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
    "qwen": "qwen-plus",
    "gemini": "gemini-2.0-flash-exp",
    "zhipu": "glm-4-flash",
    "grok": "grok-beta",
    "openrouter": "anthropic/claude-3.5-sonnet",
}


def update_config(provider: str, api_key: str, model: str | None = None) -> None:
    """
    更新配置文件

    Args:
        provider: LLM 提供商
        api_key: API Key
        model: 模型名称（可选，会根据 provider 设置默认值）
    """
    # 确定配置文件路径
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config" / "settings.yaml"
    template_path = project_root / "config" / "settings.example.yaml"

    # 如果配置文件不存在，从模板创建
    if not config_path.exists():
        if template_path.exists():
            config_path.write_text(template_path.read_text())
            print(f"📄 从模板创建配置文件: {config_path}")
        else:
            print(f"❌ 模板文件不存在: {template_path}")
            sys.exit(1)

    # 读取配置
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # 更新 LLM 配置
    if "llm" not in config:
        config["llm"] = {}

    config["llm"]["provider"] = provider

    # 设置模型
    final_model = model or DEFAULT_MODELS.get(provider, "")
    if final_model:
        config["llm"]["model"] = final_model

    # 更新 API Key
    config["llm"]["api_key"] = api_key

    # 写回配置
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"✅ 配置已更新:")
    print(f"   Provider: {provider}")
    print(f"   Model: {config['llm'].get('model', '(未设置)')}")
    print(f"   API Key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else '***'}")


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python scripts/update_config.py <provider> <api_key> [model]")
        print()
        print("Supported providers:", ", ".join(DEFAULT_MODELS.keys()))
        sys.exit(1)

    provider = sys.argv[1].lower()
    api_key = sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else None

    # 验证提供商
    valid_providers = list(DEFAULT_MODELS.keys())
    if provider not in valid_providers:
        print(f"❌ 不支持的提供商: {provider}")
        print(f"   支持的提供商: {', '.join(valid_providers)}")
        sys.exit(1)

    update_config(provider, api_key, model)


if __name__ == "__main__":
    main()

