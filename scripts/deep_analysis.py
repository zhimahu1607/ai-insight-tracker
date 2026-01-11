#!/usr/bin/env python3
"""
深度分析入口脚本

解析 GitHub Issue，执行 Multi-Agent 深度分析，保存结果并发送通知。

Usage:
    python scripts/deep_analysis.py \\
        --issue-number 123 \\
        --issue-title "[Analysis] 2501.12345: Paper Title" \\
        --issue-body "分析需求..."

Exit codes:
    0: 成功
    1: 参数错误
    2: 论文不存在
    3: 分析失败
"""

import argparse
import asyncio
import logging
import re
import sys
from pathlib import Path
from typing import Optional

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import check_required_config
from src.data_fetchers.arxiv import fetch_arxiv_paper_by_id
from src.agents.paper.deep_analyzer import run_deep_analysis
from src.notifiers.feishu import get_notifier


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# 数据目录
DATA_DIR = project_root / "data"
ANALYSIS_DIR = DATA_DIR / "analysis" / "deep"


def parse_issue_title(title: str) -> tuple[Optional[str], Optional[str]]:
    """
    解析 Issue 标题，提取论文 ID 和标题

    Args:
        title: Issue 标题，格式: "[Analysis] 2501.12345: Paper Title"

    Returns:
        (paper_id, paper_title) 或 (None, None)

    Examples:
        >>> parse_issue_title("[Analysis] 2501.12345: Some Paper Title")
        ('2501.12345', 'Some Paper Title')

        >>> parse_issue_title("[Analysis] 2501.12345v2: Paper with version")
        ('2501.12345', 'Paper with version')
    """
    # 匹配模式: [Analysis] {paper_id}: {title}
    # paper_id 可能带版本号如 2501.12345v2
    pattern = r"\[Analysis\]\s*(\d+\.\d+)(?:v\d+)?:\s*(.+)"
    match = re.match(pattern, title, re.IGNORECASE)

    if match:
        paper_id = match.group(1)
        paper_title = match.group(2).strip()
        return paper_id, paper_title

    return None, None


def save_analysis_result(paper_id: str, report: str) -> Path:
    """
    保存分析结果到 Markdown 文件

    Args:
        paper_id: 论文 ID
        report: 分析报告（Markdown）

    Returns:
        保存的文件路径
    """
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    # 文件名: {paper_id}.md
    file_path = ANALYSIS_DIR / f"{paper_id}.md"
    file_path.write_text(report, encoding="utf-8")

    logger.info(f"分析结果已保存: {file_path}")
    return file_path


async def send_notification(
    paper_id: str,
    paper_title: str,
    summary: str,
    issue_url: str,
) -> bool:
    """
    发送深度分析完成通知

    Args:
        paper_id: 论文 ID
        paper_title: 论文标题
        summary: 分析摘要
        issue_url: GitHub Issue 链接

    Returns:
        发送是否成功
    """
    notifier = get_notifier()
    try:
        return await notifier.send_deep_analysis(
            paper_id=paper_id,
            paper_title=paper_title,
            summary=summary,
            issue_url=issue_url,
        )
    finally:
        await notifier.close()


def extract_summary_from_report(report: str, max_length: int = 500) -> str:
    """
    从报告中提取摘要

    Args:
        report: 完整报告
        max_length: 最大长度

    Returns:
        摘要文本
    """
    # 移除 Markdown 标题
    lines = report.split("\n")
    content_lines = []
    for line in lines:
        # 跳过标题行
        if line.startswith("#"):
            continue
        # 跳过空行
        if not line.strip():
            continue
        content_lines.append(line.strip())

    content = " ".join(content_lines)

    if len(content) > max_length:
        content = content[:max_length] + "..."

    return content


async def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="AI Insight Tracker 深度分析脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--issue-number",
        type=int,
        required=True,
        help="GitHub Issue 编号",
    )
    parser.add_argument(
        "--issue-title",
        type=str,
        required=True,
        help="Issue 标题，格式: [Analysis] {paper_id}: {title}",
    )
    parser.add_argument(
        "--issue-body",
        type=str,
        default="",
        help="Issue 正文，包含用户指定的分析需求",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default="",
        help="仓库名称，格式: owner/repo（用于构建 Issue URL）",
    )
    parser.add_argument(
        "--skip-config-check",
        action="store_true",
        help="跳过配置检查",
    )

    args = parser.parse_args()

    # 配置检查
    if not args.skip_config_check:
        is_valid, errors = check_required_config()
        if not is_valid:
            logger.error("配置验证失败:")
            for error in errors:
                logger.error(f"  - {error}")
            return 1

    # 解析 Issue 标题
    paper_id, paper_title = parse_issue_title(args.issue_title)
    if not paper_id:
        logger.error(f"无法解析 Issue 标题: {args.issue_title}")
        logger.error("期望格式: [Analysis] 2501.12345: Paper Title")
        return 1

    logger.info(f"解析成功: paper_id={paper_id}, title={paper_title}")

    # 获取论文详情
    logger.info(f"获取论文详情: {paper_id}")
    paper = await fetch_arxiv_paper_by_id(paper_id)
    if not paper:
        logger.error(f"论文不存在: {paper_id}")
        return 2

    # 执行深度分析
    try:
        logger.info(f"开始深度分析(全文): {paper.id} - {paper.title}")
        result = await run_deep_analysis(
            paper_id=paper.id,
            paper_title=paper.title,
            paper_abstract=paper.abstract,
            requirements=args.issue_body or "",
        )
        logger.info(
            f"深度分析完成: {paper.id} (fulltext_parse_status={result.fulltext_parse_status}, sections={result.paper_total_sections})"
        )
        report = result.report
    except Exception as e:
        logger.exception(f"深度分析失败: {e}")
        return 3

    # 保存分析结果
    save_analysis_result(paper_id, report)

    # 发送通知
    if args.repo:
        issue_url = f"https://github.com/{args.repo}/issues/{args.issue_number}"
    else:
        issue_url = ""

    if issue_url:
        summary = extract_summary_from_report(report)
        await send_notification(
            paper_id=paper_id,
            paper_title=paper.title,
            summary=summary,
            issue_url=issue_url,
        )

    logger.info("深度分析任务完成")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

