#!/usr/bin/env python3
"""
配置验证脚本

验证配置完整性，输出格式化的验证结果。
区分错误（阻断执行）和警告（可继续执行）。

Usage:
    python scripts/validate_config.py

Exit codes:
    0: 验证通过（可能有警告）
    1: 验证失败（有错误）
"""

import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import load_settings_without_validation


console = Console()


def validate_config() -> int:
    """
    验证配置，区分错误和警告

    Returns:
        0: 验证通过（可能有警告）
        1: 验证失败（有错误）
    """
    settings = load_settings_without_validation()

    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    # === 必填项检查 (Error) ===
    if not settings.llm.provider:
        errors.append("llm.provider 是必填项")
    if not settings.llm.model:
        errors.append("llm.model 是必填项")
    if not settings.llm.api_key:
        errors.append("llm.api_key 是必填项")

    # === 可选项检查 (Warning) ===
    if not settings.notification.feishu_webhook_url:
        warnings.append("feishu_webhook_url 未配置，通知功能将不可用")
    if settings.search.api == "tavily" and not settings.search.tavily_api_key:
        warnings.append("tavily_api_key 未配置，深度分析将使用 DuckDuckGo")

    # === 信息提示 (Info) ===
    if settings.llm.provider:
        info.append(f"LLM 提供商: {settings.llm.provider}")
    if settings.llm.model:
        info.append(f"LLM 模型: {settings.llm.model}")
    info.append(f"arXiv 分类: {', '.join(settings.arxiv.categories)}")

    # 输出结果
    console.print()

    if errors:
        error_text = "\n".join(f"  • {e}" for e in errors)
        console.print(Panel(
            f"[bold red]配置验证失败，以下必填项缺失：[/bold red]\n\n{error_text}",
            title="❌ 错误",
            border_style="red",
        ))
        console.print()
        console.print("[yellow]请通过以下方式之一完成配置：[/yellow]")
        console.print("  1. 运行 [green]./setup.sh[/green]")
        console.print("  2. 编辑 [green]config/settings.yaml[/green]")
        console.print("  3. 设置环境变量 [green]LLM_PROVIDER[/green], [green]LLM_MODEL[/green], [green]LLM_API_KEY[/green]")
        console.print()
        return 1

    if warnings:
        warning_text = "\n".join(f"  • {w}" for w in warnings)
        console.print(Panel(
            f"[bold yellow]以下可选项未配置：[/bold yellow]\n\n{warning_text}",
            title="⚠️ 警告",
            border_style="yellow",
        ))
        console.print()

    # 显示配置信息
    if info:
        table = Table(title="配置信息", show_header=True, header_style="bold cyan")
        table.add_column("配置项", style="cyan")
        table.add_column("值", style="green")
        for item in info:
            parts = item.split(": ", 1)
            if len(parts) == 2:
                table.add_row(parts[0], parts[1])
        console.print(table)
        console.print()

    console.print("[bold green]✅ 配置验证通过[/bold green]")
    console.print()
    return 0


if __name__ == "__main__":
    sys.exit(validate_config())

