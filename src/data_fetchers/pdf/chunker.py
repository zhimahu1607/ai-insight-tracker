"""
论文智能分块器

将论文内容按语义分块，适合 LLM 处理。
"""

from typing import Optional

from .models import PaperSection, ParsedPaper, SectionType


class PaperChunker:
    """
    论文智能分块器

    将论文内容按语义分块，适合 LLM 处理。

    策略：
    1. 优先按章节分块
    2. 超长章节按段落分割
    3. 保留上下文重叠
    """

    def __init__(
        self,
        max_tokens_per_chunk: int = 4000,
        overlap_tokens: int = 200,
    ):
        """
        初始化分块器

        Args:
            max_tokens_per_chunk: 每个分块的最大 token 数
            overlap_tokens: 分块之间的重叠 token 数
        """
        self._max_tokens = max_tokens_per_chunk
        self._overlap = overlap_tokens

    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数"""
        return int(len(text) * 0.75)

    def _split_long_section(self, section: PaperSection) -> list[PaperSection]:
        """分割过长的章节"""
        if section.token_count <= self._max_tokens:
            return [section]

        # 按段落分割（使用双换行或单换行 + 句号）
        paragraphs = section.content.replace(". ", ".\n").split("\n")
        chunks: list[PaperSection] = []
        current_chunk = ""
        chunk_index = 1

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_tokens = self._estimate_tokens(para)
            current_tokens = self._estimate_tokens(current_chunk)

            if current_tokens + para_tokens <= self._max_tokens:
                current_chunk += para + " "
            else:
                # 保存当前块
                if current_chunk.strip():
                    chunks.append(
                        PaperSection(
                            section_type=section.section_type,
                            title=f"{section.title} (Part {chunk_index})",
                            content=current_chunk.strip(),
                            page_start=section.page_start,
                            page_end=section.page_end,
                            token_count=self._estimate_tokens(current_chunk),
                        )
                    )
                    chunk_index += 1

                # 开始新块（带重叠）
                overlap_chars = int(self._overlap / 0.75)
                overlap_text = (
                    current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else ""
                )
                current_chunk = overlap_text + para + " "

        # 保存最后一块
        if current_chunk.strip():
            chunks.append(
                PaperSection(
                    section_type=section.section_type,
                    title=f"{section.title} (Part {chunk_index})" if chunk_index > 1 else section.title,
                    content=current_chunk.strip(),
                    page_start=section.page_start,
                    page_end=section.page_end,
                    token_count=self._estimate_tokens(current_chunk),
                )
            )

        return chunks if chunks else [section]

    def chunk(self, paper: ParsedPaper) -> list[PaperSection]:
        """
        对论文进行分块

        Args:
            paper: 解析后的论文

        Returns:
            分块后的章节列表
        """
        chunks: list[PaperSection] = []

        for section in paper.sections:
            # 跳过参考文献（单独处理）
            if section.section_type == SectionType.REFERENCES:
                continue

            # 分割过长的章节
            section_chunks = self._split_long_section(section)
            chunks.extend(section_chunks)

        return chunks

    def get_section_by_type(
        self,
        paper: ParsedPaper,
        section_type: SectionType,
    ) -> Optional[str]:
        """
        获取指定类型的章节内容

        Args:
            paper: 解析后的论文
            section_type: 章节类型

        Returns:
            章节内容，不存在返回 None
        """
        for section in paper.sections:
            if section.section_type == section_type:
                return section.content
        return None

    def get_summary_context(self, paper: ParsedPaper, max_tokens: int = 6000) -> str:
        """
        获取论文摘要上下文（用于给 Writer 提供概览）

        优先包含：Abstract, Introduction, Method 概要, Conclusion

        Args:
            paper: 解析后的论文
            max_tokens: 最大 token 数

        Returns:
            精选的论文内容
        """
        priority_types = [
            SectionType.ABSTRACT,
            SectionType.INTRODUCTION,
            SectionType.CONCLUSION,
            SectionType.METHOD,
            SectionType.EXPERIMENT,
            SectionType.RESULTS,
        ]

        context_parts: list[str] = []
        current_tokens = 0

        for section_type in priority_types:
            content = self.get_section_by_type(paper, section_type)
            if content:
                tokens = self._estimate_tokens(content)
                if current_tokens + tokens <= max_tokens:
                    section_name = section_type.value.replace("_", " ").title()
                    context_parts.append(f"## {section_name}\n{content}")
                    current_tokens += tokens
                else:
                    # 截断
                    available = max_tokens - current_tokens
                    if available > 500:
                        chars_available = int(available / 0.75)
                        truncated = content[:chars_available]
                        section_name = section_type.value.replace("_", " ").title()
                        context_parts.append(
                            f"## {section_name} (truncated)\n{truncated}..."
                        )
                    break

        return "\n\n".join(context_parts)

    def get_tables_context(self, paper: ParsedPaper, max_tables: int = 5) -> str:
        """
        获取表格内容上下文

        Args:
            paper: 解析后的论文
            max_tables: 最大表格数

        Returns:
            表格内容文本
        """
        if not paper.tables:
            return ""

        table_texts: list[str] = []
        for table in paper.tables[:max_tables]:
            header = f"### {table.table_id}"
            if table.caption:
                header += f": {table.caption}"
            table_texts.append(f"{header}\n\n{table.raw_text}")

        return "\n\n".join(table_texts)

    def get_figures_context(self, paper: ParsedPaper) -> str:
        """
        获取图表说明上下文

        Args:
            paper: 解析后的论文

        Returns:
            图表说明文本
        """
        if not paper.figures:
            return ""

        figure_texts: list[str] = []
        for fig in paper.figures:
            figure_texts.append(f"- **{fig.figure_id}** (Page {fig.page}): {fig.caption}")

        return "\n".join(figure_texts)

