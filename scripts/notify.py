#!/usr/bin/env python3
"""
通知脚本

发送每日报告或深度分析结果到飞书。

Usage:
    # 发送每日报告
    python scripts/notify.py --type daily

    # 发送深度分析结果
    python scripts/notify.py --type deep --paper-id 2501.12345 --issue-url "https://github.com/..."

Exit codes:
    0: 成功
    1: 参数错误
    2: 数据不存在
    3: 发送失败
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings
from src.models import DailyReport
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
REPORTS_DIR = DATA_DIR / "reports"
ANALYSIS_DIR = DATA_DIR / "analysis" / "deep"


def get_today_date() -> str:
    """获取今天的日期字符串 YYYY-MM-DD"""
    return datetime.now().strftime("%Y-%m-%d")


async def send_daily_report(date: str | None = None) -> bool:
    """
    发送每日报告通知

    Args:
        date: 报告日期，默认为今天

    Returns:
        发送是否成功
    """
    report_date = date or get_today_date()
    report_file = REPORTS_DIR / f"{report_date}.json"

    if not report_file.exists():
        logger.error(f"日报文件不存在: {report_file}")
        return False

    # 加载日报
    report_data = json.loads(report_file.read_text(encoding="utf-8"))
    report = DailyReport.model_validate(report_data)

    logger.info(f"加载日报: {report_date}")
    logger.info(f"  - 论文: {report.stats.total_papers} 篇")
    logger.info(f"  - 热点: {report.stats.total_news} 条")

    # 发送通知
    notifier = get_notifier()
    try:
        success = await notifier.send_daily_report(report)
        if success:
            logger.info("日报通知发送成功")
        else:
            logger.warning("日报通知发送失败或未配置")
        return success
    finally:
        await notifier.close()


async def send_deep_analysis(
    paper_id: str,
    issue_url: str,
) -> bool:
    """
    发送深度分析结果通知

    Args:
        paper_id: 论文 ID
        issue_url: GitHub Issue 链接

    Returns:
        发送是否成功
    """
    analysis_file = ANALYSIS_DIR / f"{paper_id}.md"

    if not analysis_file.exists():
        logger.error(f"分析结果文件不存在: {analysis_file}")
        return False

    # 读取分析结果
    report = analysis_file.read_text(encoding="utf-8")

    # 提取标题（第一行 # 开头）
    lines = report.split("\n")
    paper_title = paper_id
    for line in lines:
        if line.startswith("# "):
            paper_title = line[2:].strip()
            break

    # 提取摘要（前 500 字符）
    content_lines = [l for l in lines if not l.startswith("#") and l.strip()]
    summary = " ".join(content_lines)[:500]
    if len(summary) == 500:
        summary += "..."

    logger.info(f"加载深度分析: {paper_id}")
    logger.info(f"  - 标题: {paper_title}")
    logger.info(f"  - 内容长度: {len(report)} 字符")

    # 发送通知
    notifier = get_notifier()
    try:
        success = await notifier.send_deep_analysis(
            paper_id=paper_id,
            paper_title=paper_title,
            summary=summary,
            issue_url=issue_url,
        )
        if success:
            logger.info("深度分析通知发送成功")
        else:
            logger.warning("深度分析通知发送失败或未配置")
        return success
    finally:
        await notifier.close()


async def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="AI Insight Tracker 通知脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--type",
        choices=["daily", "deep"],
        required=True,
        help="通知类型: daily=日报, deep=深度分析",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="日报日期，格式 YYYY-MM-DD（仅 daily 类型使用）",
    )
    parser.add_argument(
        "--paper-id",
        type=str,
        default=None,
        help="论文 ID（仅 deep 类型使用）",
    )
    parser.add_argument(
        "--issue-url",
        type=str,
        default=None,
        help="GitHub Issue 链接（仅 deep 类型使用）",
    )

    args = parser.parse_args()

    if args.type == "daily":
        success = await send_daily_report(args.date)
        return 0 if success else 3

    elif args.type == "deep":
        if not args.paper_id:
            logger.error("深度分析通知需要指定 --paper-id")
            return 1
        if not args.issue_url:
            logger.error("深度分析通知需要指定 --issue-url")
            return 1

        success = await send_deep_analysis(args.paper_id, args.issue_url)
        return 0 if success else 3

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

