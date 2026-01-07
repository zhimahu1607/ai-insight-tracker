"""
PDF 处理模块

提供 arXiv 论文 PDF 的下载、解析和分块能力。

Usage:
    from src.data_fetchers.pdf import load_paper_pdf

    # 一站式加载论文 PDF
    parsed_paper = await load_paper_pdf(
        paper_id="2501.12345",
        paper_title="Paper Title",
        pdf_url="https://arxiv.org/pdf/2501.12345.pdf",
    )

    # 获取摘要上下文
    from src.data_fetchers.pdf import PaperChunker
    chunker = PaperChunker()
    context = chunker.get_summary_context(parsed_paper)
"""

import logging
from pathlib import Path
from typing import Optional

from .models import (
    FigureInfo,
    PaperSection,
    ParsedPaper,
    Reference,
    SectionType,
    TableInfo,
)
from .downloader import PDFDownloader
from .parser import PDFParser
from .chunker import PaperChunker

logger = logging.getLogger(__name__)

__all__ = [
    # 数据模型
    "ParsedPaper",
    "PaperSection",
    "SectionType",
    "TableInfo",
    "FigureInfo",
    "Reference",
    # 核心类
    "PDFDownloader",
    "PDFParser",
    "PaperChunker",
    # 便捷函数
    "load_paper_pdf",
]


async def load_paper_pdf(
    paper_id: str,
    paper_title: str = "",
    pdf_url: Optional[str] = None,
    download_timeout: float = 120.0,
) -> ParsedPaper:
    """
    一站式加载论文 PDF

    下载 -> 解析 -> 清理临时文件

    Args:
        paper_id: arXiv 论文 ID
        paper_title: 论文标题
        pdf_url: PDF URL（可选，默认根据 ID 构建）
        download_timeout: 下载超时时间（秒）

    Returns:
        ParsedPaper: 解析后的论文结构

    Note:
        如果下载或解析失败，返回的 ParsedPaper 的 parse_status 为 "failed"
    """
    pdf_path: Optional[Path] = None

    try:
        # 下载 PDF
        downloader = PDFDownloader(timeout=download_timeout)
        pdf_path = await downloader.download(paper_id, pdf_url)

        # 解析 PDF
        parser = PDFParser()
        parsed_paper = parser.parse(pdf_path, paper_id, paper_title)

        return parsed_paper

    except Exception as e:
        logger.error(f"加载论文 PDF 失败: {paper_id}, 错误: {e}")
        return ParsedPaper(
            paper_id=paper_id,
            title=paper_title,
            parse_status="failed",
            parse_error=str(e),
        )

    finally:
        # 清理临时文件
        if pdf_path is not None:
            PDFDownloader.cleanup(pdf_path)

