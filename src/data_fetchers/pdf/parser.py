"""
学术论文 PDF 解析器

使用 PyMuPDF 提取文本，pdfplumber 提取表格。
支持按章节分块、图表说明提取、参考文献解析。
"""

import logging
import re
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import pdfplumber

from .models import (
    FigureInfo,
    PaperSection,
    ParsedPaper,
    Reference,
    SectionType,
    TableInfo,
)

logger = logging.getLogger(__name__)

# 章节标题识别模式
SECTION_PATTERNS: dict[SectionType, str] = {
    SectionType.ABSTRACT: r"^abstract\s*$",
    SectionType.INTRODUCTION: r"^(?:\d+\.?\s*)?introduction\s*$",
    SectionType.RELATED_WORK: r"^(?:\d+\.?\s*)?(?:related\s+work|background|literature\s+review|preliminary|preliminaries)\s*$",
    SectionType.METHOD: r"^(?:\d+\.?\s*)?(?:method(?:s|ology)?|approach|framework|proposed\s+method|our\s+method|model)\s*$",
    SectionType.EXPERIMENT: r"^(?:\d+\.?\s*)?(?:experiment(?:s|al)?(?:\s+setup)?|evaluation|implementation)\s*$",
    SectionType.RESULTS: r"^(?:\d+\.?\s*)?(?:results?|findings|main\s+results)\s*$",
    SectionType.DISCUSSION: r"^(?:\d+\.?\s*)?(?:discussion|analysis)\s*$",
    SectionType.CONCLUSION: r"^(?:\d+\.?\s*)?(?:conclusion(?:s)?|summary|summary\s+and\s+conclusion)\s*$",
    SectionType.REFERENCES: r"^(?:references?|bibliography)\s*$",
    SectionType.APPENDIX: r"^(?:appendix|appendices|supplementary|supplemental)\s*",
}


class PDFParser:
    """
    学术论文 PDF 解析器

    使用 PyMuPDF 提取文本，pdfplumber 提取表格。

    Features:
        - 按章节分块
        - 表格提取（使用 pdfplumber）
        - 图表说明提取
        - 参考文献解析
    """

    def __init__(
        self,
        estimate_tokens_ratio: float = 0.75,
    ):
        """
        初始化解析器

        Args:
            estimate_tokens_ratio: 字符数转 token 数的比例
        """
        self._token_ratio = estimate_tokens_ratio

    def _estimate_tokens(self, text: str) -> int:
        """估算文本的 token 数"""
        return int(len(text) * self._token_ratio)

    def _identify_section_type(self, title: str) -> SectionType:
        """识别章节类型"""
        title_lower = title.lower().strip()
        for section_type, pattern in SECTION_PATTERNS.items():
            if re.match(pattern, title_lower, re.IGNORECASE):
                return section_type
        return SectionType.OTHER

    def _extract_figures(self, doc: fitz.Document) -> list[FigureInfo]:
        """提取图表信息"""
        figures: list[FigureInfo] = []
        figure_pattern = re.compile(
            r"(Figure|Fig\.?)\s*(\d+)[.:]?\s*(.+?)(?=\n\n|Figure|Fig\.|\Z)",
            re.IGNORECASE | re.DOTALL,
        )

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            for match in figure_pattern.finditer(text):
                figure_id = f"Figure {match.group(2)}"
                caption = match.group(3).strip()[:500]  # 限制长度
                # 清理 caption 中的换行
                caption = " ".join(caption.split())
                figures.append(
                    FigureInfo(
                        figure_id=figure_id,
                        caption=caption,
                        page=page_num + 1,
                    )
                )

        # 去重（同一个图可能在多个位置被匹配）
        seen_ids: set[str] = set()
        unique_figures: list[FigureInfo] = []
        for fig in figures:
            if fig.figure_id not in seen_ids:
                seen_ids.add(fig.figure_id)
                unique_figures.append(fig)

        return unique_figures

    def _extract_tables(self, pdf_path: Path) -> list[TableInfo]:
        """
        使用 pdfplumber 提取表格

        Args:
            pdf_path: PDF 文件路径

        Returns:
            表格信息列表
        """
        tables: list[TableInfo] = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    for idx, table in enumerate(page_tables):
                        if not table or len(table) < 2:
                            continue

                        # 提取表头和数据行
                        headers = [str(cell) if cell else "" for cell in table[0]]
                        rows = [
                            [str(cell) if cell else "" for cell in row]
                            for row in table[1:]
                        ]

                        # 生成原始文本表示
                        raw_text = self._table_to_text(headers, rows)

                        # 尝试从页面文本中提取表格标题
                        table_id = f"Table {len(tables) + 1}"
                        caption = self._find_table_caption(page, len(tables) + 1)

                        tables.append(
                            TableInfo(
                                table_id=table_id,
                                caption=caption,
                                page=page_num,
                                headers=headers,
                                rows=rows,
                                raw_text=raw_text,
                            )
                        )

        except Exception as e:
            logger.warning(f"表格提取失败: {e}")

        return tables

    def _table_to_text(self, headers: list[str], rows: list[list[str]]) -> str:
        """将表格转换为文本格式"""
        lines = []

        # 表头
        if headers:
            lines.append(" | ".join(headers))
            lines.append("-" * 50)

        # 数据行
        for row in rows[:20]:  # 限制行数
            lines.append(" | ".join(row))

        if len(rows) > 20:
            lines.append(f"... (共 {len(rows)} 行)")

        return "\n".join(lines)

    def _find_table_caption(
        self, page: "pdfplumber.page.Page", table_num: int
    ) -> Optional[str]:
        """尝试从页面文本中提取表格标题"""
        text = page.extract_text() or ""
        pattern = re.compile(
            rf"Table\s*{table_num}[.:]?\s*(.+?)(?=\n\n|Table\s*\d|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(text)
        if match:
            caption = match.group(1).strip()[:300]
            return " ".join(caption.split())
        return None

    def _extract_references(self, ref_text: str) -> list[Reference]:
        """解析参考文献"""
        references: list[Reference] = []

        # 按编号分割：[1], [2] 或 1., 2. 格式
        ref_pattern = re.compile(
            r"(?:^\[(\d+)\]|^(\d+)\.)\s*(.+?)(?=(?:^\[|\n\d+\.|\Z))",
            re.MULTILINE | re.DOTALL,
        )

        for match in ref_pattern.finditer(ref_text):
            index = int(match.group(1) or match.group(2))
            raw_text = match.group(3).strip()

            # 清理换行
            raw_text = " ".join(raw_text.split())

            # 尝试提取 arXiv ID
            arxiv_match = re.search(
                r"arXiv[:\s]*(\d{4}\.\d{4,5})", raw_text, re.IGNORECASE
            )
            arxiv_id = arxiv_match.group(1) if arxiv_match else None

            # 尝试提取 DOI
            doi_match = re.search(r"10\.\d{4,}/[^\s]+", raw_text)
            doi = doi_match.group(0).rstrip(".,;") if doi_match else None

            # 尝试提取年份
            year_match = re.search(r"\b(19|20)\d{2}\b", raw_text)
            year = int(year_match.group(0)) if year_match else None

            references.append(
                Reference(
                    index=index,
                    raw_text=raw_text[:1000],  # 限制长度
                    arxiv_id=arxiv_id,
                    doi=doi,
                    year=year,
                )
            )

        return references

    def _split_into_sections(
        self,
        doc: fitz.Document,
    ) -> list[PaperSection]:
        """
        将文档分割为章节

        使用字体大小和格式识别标题，然后按标题分块。
        """
        sections: list[PaperSection] = []
        current_section: Optional[dict] = None

        for page_num in range(len(doc)):
            page = doc[page_num]
            # 获取文本块及其格式信息
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    line_text = ""
                    max_font_size = 0
                    is_bold = False

                    for span in line["spans"]:
                        text = span["text"]
                        font_size = span["size"]
                        line_text += text
                        max_font_size = max(max_font_size, font_size)
                        if "bold" in span["font"].lower():
                            is_bold = True

                    line_text = line_text.strip()
                    if not line_text:
                        continue

                    # 检测是否为章节标题
                    section_type = self._identify_section_type(line_text)
                    is_title = (
                        section_type != SectionType.OTHER
                        and max_font_size >= 10
                        and (is_bold or max_font_size >= 12)
                        and len(line_text) < 100
                    )

                    if is_title:
                        # 保存上一个章节
                        if current_section:
                            sections.append(self._finalize_section(current_section))

                        # 开始新章节
                        current_section = {
                            "type": section_type,
                            "title": line_text,
                            "content": "",
                            "page_start": page_num + 1,
                            "page_end": page_num + 1,
                        }
                    elif current_section:
                        # 添加内容到当前章节
                        current_section["content"] += line_text + " "
                        current_section["page_end"] = page_num + 1

        # 保存最后一个章节
        if current_section:
            sections.append(self._finalize_section(current_section))

        return sections

    def _finalize_section(self, section_dict: dict) -> PaperSection:
        """完成章节处理"""
        content = section_dict["content"].strip()
        # 清理多余空格
        content = " ".join(content.split())

        token_count = self._estimate_tokens(content)

        return PaperSection(
            section_type=section_dict["type"],
            title=section_dict["title"],
            content=content,
            page_start=section_dict["page_start"],
            page_end=section_dict["page_end"],
            token_count=token_count,
        )

    def parse(self, pdf_path: Path, paper_id: str, title: str = "") -> ParsedPaper:
        """
        解析 PDF 文件

        Args:
            pdf_path: PDF 文件路径
            paper_id: 论文 ID
            title: 论文标题

        Returns:
            ParsedPaper: 解析后的论文结构
        """
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            # 提取全文
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"

            # 按章节分割
            sections = self._split_into_sections(doc)

            # 提取图表
            figures = self._extract_figures(doc)

            doc.close()

            # 提取表格（使用 pdfplumber）
            tables = self._extract_tables(pdf_path)

            # 提取参考文献
            references: list[Reference] = []
            for section in sections:
                if section.section_type == SectionType.REFERENCES:
                    references = self._extract_references(section.content)
                    break

            # 计算总 token 数
            total_tokens = self._estimate_tokens(full_text)

            logger.info(
                f"PDF 解析完成: {paper_id}, "
                f"页数={total_pages}, 章节={len(sections)}, "
                f"表格={len(tables)}, 图表={len(figures)}, 参考文献={len(references)}"
            )

            return ParsedPaper(
                paper_id=paper_id,
                title=title,
                full_text=full_text,
                total_pages=total_pages,
                total_tokens=total_tokens,
                sections=sections,
                tables=tables,
                figures=figures,
                references=references,
                parse_status="success",
            )

        except Exception as e:
            logger.error(f"PDF 解析失败: {e}")
            return ParsedPaper(
                paper_id=paper_id,
                title=title,
                parse_status="failed",
                parse_error=str(e),
            )

