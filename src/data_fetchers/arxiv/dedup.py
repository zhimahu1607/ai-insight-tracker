"""
arXiv 论文去重逻辑

采用全量历史数据比较的去重策略，确保每篇论文只被处理一次。
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Paper

logger = logging.getLogger(__name__)

from src.data_fetchers.status import DedupStatus


def load_all_historical_ids(data_dir: Path) -> set[str]:
    """
    加载全量历史论文 ID

    遍历 data/papers/ 目录下所有 JSONL 文件，提取论文 ID 集合。

    Args:
        data_dir: 数据目录路径，如 Path("data/papers")

    Returns:
        历史论文 ID 集合

    Note:
        - 仅加载论文 ID（~32 字节/篇），内存占用小
        - 10 万篇论文的 ID 集合约 3MB 内存
    """
    historical_ids: set[str] = set()

    if not data_dir.exists():
        logger.info(f"数据目录不存在，跳过历史加载: {data_dir}")
        return historical_ids

    # 遍历所有 JSON 文件（兼容 .json 和 .jsonl）
    json_files = list(data_dir.glob("*.json")) + list(data_dir.glob("*.jsonl"))
    logger.info(f"加载历史数据: 发现 {len(json_files)} 个文件")

    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if file_path.suffix == '.json':
                    try:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                paper_id = item.get("id")
                                if paper_id:
                                    historical_ids.add(paper_id)
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析 JSON 失败 ({file_path}): {e}")
                else:  # .jsonl
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            paper_id = data.get("id")
                            if paper_id:
                                historical_ids.add(paper_id)
                        except json.JSONDecodeError as e:
                            logger.warning(f"解析行失败 ({file_path}): {e}")
                            continue
        except IOError as e:
            logger.warning(f"读取文件失败 ({file_path}): {e}")
            continue

    logger.info(f"历史数据加载完成: {len(historical_ids)} 篇论文")
    return historical_ids


def dedup_papers(
    today_papers: list["Paper"],
    historical_ids: set[str],
) -> tuple[list["Paper"], int]:
    """
    对今日论文进行全量去重

    Args:
        today_papers: 今日获取的论文列表
        historical_ids: 历史论文 ID 集合

    Returns:
        (去重后的论文列表, 状态码)

    状态码:
        - 0: 有新内容
        - 1: 无新内容
        - 2: 处理错误
    """
    try:
        if not today_papers:
            logger.info("今日无论文，跳过去重")
            return [], DedupStatus.NO_NEW_CONTENT

        # 提取今日论文 ID
        today_ids = {p.id for p in today_papers}

        # 计算新论文
        new_ids = today_ids - historical_ids
        new_papers = [p for p in today_papers if p.id in new_ids]

        # 记录去重统计
        duplicates_count = len(today_papers) - len(new_papers)
        logger.info(
            f"去重完成: 今日 {len(today_papers)} 篇, "
            f"历史重复 {duplicates_count} 篇, "
            f"新论文 {len(new_papers)} 篇"
        )

        if not new_papers:
            return [], DedupStatus.NO_NEW_CONTENT

        return new_papers, DedupStatus.HAS_NEW_CONTENT

    except Exception as e:
        logger.error(f"去重处理出错: {e}")
        return [], DedupStatus.PROCESS_ERROR


def extract_paper_ids_from_json(file_path: Path) -> set[str]:
    """
    从单个 JSON 文件提取论文 ID（支持 .json 和 .jsonl）

    Args:
        file_path: JSON 文件路径

    Returns:
        论文 ID 集合
    """
    ids: set[str] = set()

    if not file_path.exists():
        return ids

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix == '.json':
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            paper_id = item.get("id")
                            if paper_id:
                                ids.add(paper_id)
                except json.JSONDecodeError:
                    pass
            else:  # .jsonl
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        paper_id = data.get("id")
                        if paper_id:
                            ids.add(paper_id)
                    except json.JSONDecodeError:
                        continue
    except IOError:
        pass

    return ids

