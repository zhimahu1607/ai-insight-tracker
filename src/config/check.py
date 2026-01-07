"""
首次运行检测

检测配置文件和必要配置是否存在，提供友好的引导信息。
"""

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from .loader import _find_config_file, load_settings_without_validation


console = Console()


def check_first_run() -> bool:
    """
    检测是否为首次运行

    检查配置文件是否存在。

    Returns:
        True 如果是首次运行（配置文件不存在）
    """
    config_path = _find_config_file()
    return not config_path.exists()


def show_first_run_guide() -> None:
    """显示首次运行引导信息"""
    guide = """
[bold yellow]欢迎使用 AI Insight Tracker![/bold yellow]

检测到这是首次运行，请先完成配置：

[bold cyan]方式 1: 运行初始化脚本 (推荐)[/bold cyan]
  [green]./setup.sh[/green]

[bold cyan]方式 2: 手动配置[/bold cyan]
  1. 复制配置模板:
     [green]cp config/settings.example.yaml config/settings.yaml[/green]
  2. 编辑配置文件:
     [green]vim config/settings.yaml[/green]

[bold cyan]方式 3: 设置环境变量[/bold cyan]
  [green]export LLM_PROVIDER=deepseek[/green]
  [green]export LLM_MODEL=deepseek-chat[/green]
  [green]export LLM_API_KEY=your-api-key[/green]

配置完成后，重新运行程序即可。
"""
    console.print(Panel(guide, title="🚀 首次运行配置", border_style="blue"))


def check_required_config() -> tuple[bool, list[str]]:
    """
    检查必要配置是否完整

    Returns:
        (is_valid, errors): 是否有效，错误信息列表
    """
    settings = load_settings_without_validation()
    errors: list[str] = []

    if not settings.llm.provider:
        errors.append("llm.provider 未配置")
    if not settings.llm.model:
        errors.append("llm.model 未配置")
    if not settings.llm.api_key:
        errors.append("llm.api_key 未配置")

    return len(errors) == 0, errors


def show_config_errors(errors: list[str]) -> None:
    """显示配置错误信息"""
    error_text = "\n".join(f"  • {e}" for e in errors)
    message = f"""
[bold red]配置不完整，缺少以下必填项:[/bold red]

{error_text}

[bold cyan]请通过以下方式之一完成配置:[/bold cyan]

1. 编辑配置文件:
   [green]vim config/settings.yaml[/green]

2. 设置环境变量:
   [green]export LLM_PROVIDER=deepseek[/green]
   [green]export LLM_MODEL=deepseek-chat[/green]
   [green]export LLM_API_KEY=your-api-key[/green]
"""
    console.print(Panel(message, title="❌ 配置错误", border_style="red"))


def ensure_config() -> bool:
    """
    确保配置完整

    检查配置状态，如果不完整则显示引导信息。

    Returns:
        True 如果配置完整，False 如果不完整
    """
    # 检查首次运行
    if check_first_run():
        show_first_run_guide()
        return False

    # 检查必要配置
    is_valid, errors = check_required_config()
    if not is_valid:
        show_config_errors(errors)
        return False

    return True


def ensure_config_or_exit() -> None:
    """
    确保配置完整，否则退出程序

    适用于脚本入口点。
    """
    if not ensure_config():
        sys.exit(1)

