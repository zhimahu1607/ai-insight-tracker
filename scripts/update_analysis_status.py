#!/usr/bin/env python3
"""
更新深度分析状态文件
用于在 GitHub Actions 中记录正在进行的分析任务，防止重复分析
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
STATUS_FILE = PROJECT_ROOT / "data" / "analysis" / "deep_analysis_status.json"


def load_status() -> dict:
    if not STATUS_FILE.exists():
        return {"processing_ids": []}
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"读取状态文件失败: {e}，将创建新文件")
        return {"processing_ids": []}


def save_status(status: dict):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


def add_id(paper_id: str):
    status = load_status()
    if paper_id not in status["processing_ids"]:
        status["processing_ids"].append(paper_id)
        save_status(status)
        logger.info(f"Added {paper_id} to processing list")
    else:
        logger.info(f"{paper_id} is already in processing list")


def remove_id(paper_id: str):
    status = load_status()
    if paper_id in status["processing_ids"]:
        status["processing_ids"].remove(paper_id)
        save_status(status)
        logger.info(f"Removed {paper_id} from processing list")
    else:
        logger.info(f"{paper_id} was not in processing list")


def main():
    parser = argparse.ArgumentParser(description="Update deep analysis status")
    parser.add_argument("action", choices=["add", "remove"], help="Action to perform")
    parser.add_argument("paper_id", help="Paper ID")

    args = parser.parse_args()

    if args.action == "add":
        add_id(args.paper_id)
    elif args.action == "remove":
        remove_id(args.paper_id)


if __name__ == "__main__":
    main()

