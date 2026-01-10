"""
file-list.json 生成器（前端数据索引）

目标：
- 统一生成 data/file-list.json，避免多处实现导致索引漂移
- 增加 last_updated 字段，便于前端展示与排障
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class FileList:
    papers: list[str]
    news: list[str]
    reports: list[str]
    last_updated: str

    def to_dict(self) -> dict:
        return {
            "papers": self.papers,
            "news": self.news,
            "reports": self.reports,
            "last_updated": self.last_updated,
        }


def _sorted_json_filenames(dir_path: Path) -> list[str]:
    if not dir_path.exists():
        return []
    return sorted([p.name for p in dir_path.glob("*.json")], reverse=True)


def build_file_list(data_dir: Path) -> FileList:
    """扫描 data 目录构建 file-list（以文件名倒序，适配 YYYY-MM-DD.json）"""
    papers = _sorted_json_filenames(data_dir / "papers")
    news = _sorted_json_filenames(data_dir / "news")
    reports = _sorted_json_filenames(data_dir / "reports")
    last_updated = datetime.now(timezone.utc).isoformat()
    return FileList(papers=papers, news=news, reports=reports, last_updated=last_updated)


def write_file_list(data_dir: Path) -> Path:
    """生成并写入 data/file-list.json，返回写入路径。"""
    data_dir.mkdir(parents=True, exist_ok=True)
    file_list = build_file_list(data_dir)
    out_path = data_dir / "file-list.json"
    out_path.write_text(
        json.dumps(file_list.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_path


