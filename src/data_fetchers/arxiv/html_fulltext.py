"""
arXiv 官方 HTML 全文抓取 + 结构化解析

约束:
- 严格只使用官方域名 arxiv.org
- 若不存在 HTML 版本或解析失败，则应让上层认为“深度分析失败”
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional
from xml.etree import ElementTree as ET

import aiohttp
from bs4 import BeautifulSoup, Tag

from src.models.arxiv_html_fulltext import (
    ArxivHtmlFulltext,
    ArxivHtmlSection,
    ArxivHtmlSource,
    ArxivHtmlStats,
)


logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
}


def _extract_version_from_entry_id(entry_id: str) -> str:
    """
    entry.id 形如:
    - http://arxiv.org/abs/2512.25075v1
    - https://arxiv.org/abs/2512.25075v3
    """
    m = re.search(r"v(\d+)$", entry_id.strip())
    if not m:
        raise ValueError(f"无法从 arXiv entry.id 提取版本号: {entry_id}")
    return f"v{m.group(1)}"


async def _fetch_arxiv_atom_entry(paper_id: str, timeout: float = 30.0) -> ET.Element:
    query_url = f"{ARXIV_API_URL}?id_list={paper_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(
            query_url, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"arXiv API 请求失败: HTTP {resp.status}")
            xml = await resp.text()
    root = ET.fromstring(xml)
    entry = root.find("atom:entry", ARXIV_NS)
    if entry is None:
        raise RuntimeError(f"arXiv API 未返回 entry: {paper_id}")
    return entry


async def resolve_latest_version(paper_id: str) -> str:
    """通过官方 arXiv API 获取最新版本号（vN）"""
    entry = await _fetch_arxiv_atom_entry(paper_id)
    entry_id_el = entry.find("atom:id", ARXIV_NS)
    if entry_id_el is None or not entry_id_el.text:
        raise RuntimeError(f"arXiv entry.id 缺失: {paper_id}")
    return _extract_version_from_entry_id(entry_id_el.text)


async def fetch_arxiv_metadata(
    paper_id: str,
) -> tuple[str, str, list[str]]:
    """
    通过 arXiv API 获取 (title, abstract, authors)
    - title/abstract 用于补全结构化输出
    """
    entry = await _fetch_arxiv_atom_entry(paper_id)

    title_el = entry.find("atom:title", ARXIV_NS)
    summary_el = entry.find("atom:summary", ARXIV_NS)
    author_els = entry.findall("atom:author", ARXIV_NS)

    title = (
        title_el.text.replace("\n", " ").strip()
        if title_el is not None and title_el.text
        else ""
    )
    abstract = summary_el.text.strip() if summary_el is not None and summary_el.text else ""

    authors: list[str] = []
    for a in author_els:
        name_el = a.find("atom:name", ARXIV_NS)
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())

    return title, abstract, authors


def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _extract_number_and_title(heading_text: str) -> tuple[Optional[str], str]:
    """
    支持:
    - "1 Introduction"
    - "3.2 Network architecture"
    - "1. Introduction"
    - "References"
    """
    text = _normalize_text(heading_text)
    m = re.match(r"^(\d+(?:\.\d+)*)(?:\.)?\s+(.*)$", text)
    if not m:
        return None, text
    number = m.group(1).rstrip(".")
    title = m.group(2).strip()
    return number, title or text


def _pick_content_root(soup: BeautifulSoup) -> Tag:
    return (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", id="content")
        or soup.body
        or soup  # type: ignore[return-value]
    )


def _extract_paragraph_text(tag: Tag) -> str:
    txt = tag.get_text(" ", strip=True)
    return _normalize_text(txt)


def _collect_front_matter(root: Tag) -> list[str]:
    # 收集第一个 h2/h3/... 前的 p 作为 front matter
    paragraphs: list[str] = []
    for el in root.descendants:
        if isinstance(el, Tag) and el.name and re.fullmatch(r"h[2-6]", el.name):
            break
        if isinstance(el, Tag) and el.name == "p":
            p = _extract_paragraph_text(el)
            if p:
                paragraphs.append(p)
        # 避免在异常页面上无限收集
        if len(paragraphs) >= 30:
            break
    return paragraphs


def _build_sections(root: Tag) -> list[ArxivHtmlSection]:
    # 先收集内容区内的 heading + p 的线性序列（保序）
    items: list[Tag] = []
    for el in root.descendants:
        if not isinstance(el, Tag) or not el.name:
            continue
        if re.fullmatch(r"h[2-6]", el.name) or el.name == "p":
            items.append(el)

    # index headings
    heading_indices = [i for i, t in enumerate(items) if re.fullmatch(r"h[2-6]", t.name or "")]
    if not heading_indices:
        return []

    # 先构造扁平 section 列表（附带 level 与 paragraphs）
    flat_sections: list[tuple[int, ArxivHtmlSection]] = []
    for idx_pos, idx in enumerate(heading_indices):
        h = items[idx]
        assert h.name is not None
        level = int(h.name[1])
        heading_text = _extract_paragraph_text(h)
        number, title = _extract_number_and_title(heading_text)

        # 收集该 heading 到下一个 “level <= current” heading 之间的段落
        end = len(items)
        for next_idx in heading_indices[idx_pos + 1 :]:
            nxt = items[next_idx]
            if nxt.name and int(nxt.name[1]) <= level:
                end = next_idx
                break

        paras: list[str] = []
        for t in items[idx + 1 : end]:
            if t.name == "p":
                p = _extract_paragraph_text(t)
                if p:
                    paras.append(p)

        flat_sections.append(
            (
                level,
                ArxivHtmlSection(
                    level=level,
                    heading=heading_text,
                    number=number,
                    title=title,
                    paragraphs=paras,
                    children=[],
                ),
            )
        )

    # 用栈把扁平列表组装成树
    roots: list[ArxivHtmlSection] = []
    stack: list[tuple[int, ArxivHtmlSection]] = []
    for lvl, sec in flat_sections:
        while stack and stack[-1][0] >= lvl:
            stack.pop()
        if stack:
            stack[-1][1].children.append(sec)
        else:
            roots.append(sec)
        stack.append((lvl, sec))

    return roots


def count_sections(sections: list[ArxivHtmlSection]) -> int:
    def _count(nodes: list[ArxivHtmlSection]) -> int:
        n = 0
        for s in nodes:
            n += 1
            n += _count(s.children)
        return n

    return _count(sections)


def build_fulltext_summary_context(
    fulltext: ArxivHtmlFulltext, max_chars: int = 20000
) -> str:
    """
    给 Writer 的“全文概要上下文”：
    - 只提供纯文本（标题/章节标题/段落）
    - 体积受限（避免 prompt 过大）
    """

    parts: list[str] = []
    if fulltext.front_matter_paragraphs:
        parts.append("## Front Matter\n")
        for p in fulltext.front_matter_paragraphs[:10]:
            parts.append(p)
            parts.append("")

    def walk(nodes: list[ArxivHtmlSection]) -> None:
        for s in nodes:
            parts.append(f"## {s.heading}")
            for p in s.paragraphs[:5]:
                parts.append(p)
            parts.append("")
            walk(s.children)

    walk(fulltext.sections)

    text = "\n".join(parts).strip()
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n...(内容已截断)"
    return text


async def fetch_arxiv_html_fulltext(
    paper_id: str,
    timeout: float = 40.0,
) -> ArxivHtmlFulltext:
    """
    获取并解析 arXiv 官方 HTML 全文（结构化输出）。

    Raises:
        RuntimeError: 任何抓取/解析失败都抛出，供上层判定“深度分析失败”
    """
    paper_id = paper_id.strip()
    if not paper_id:
        raise RuntimeError("paper_id 不能为空")

    # 1) 解析 latest version（vN）并获取基础 metadata
    version = await resolve_latest_version(paper_id)
    title, abstract, authors = await fetch_arxiv_metadata(paper_id)

    # 2) 构建官方 HTML URL 并抓取
    html_url = f"https://arxiv.org/html/{paper_id}{version}"
    headers = {
        "User-Agent": "ai-insight-tracker/1.0 (fulltext fetcher; +https://arxiv.org)"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(
            html_url, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"arXiv HTML 不存在或不可访问: HTTP {resp.status}")
            html = await resp.text()

    if not html or len(html) < 1000:
        raise RuntimeError("arXiv HTML 内容为空或过短，判定为不可用")

    # 3) 解析 HTML 为结构化章节
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()

    root = _pick_content_root(soup)
    front_matter = _collect_front_matter(root)
    sections = _build_sections(root)

    if not sections:
        # 严格策略：无结构化章节 => 认为 HTML 不可用于深度分析
        raise RuntimeError("arXiv HTML 未解析出章节结构，判定深度分析失败")

    blocks = count_sections(sections)
    # 段落数也计入 blocks，便于粗略衡量信息量
    para_blocks = 0
    stack = list(sections)
    while stack:
        s = stack.pop()
        para_blocks += len(s.paragraphs)
        stack.extend(s.children)
    blocks += para_blocks

    return ArxivHtmlFulltext(
        paper_id=paper_id,
        source=ArxivHtmlSource(
            provider="arxiv",
            url=html_url,
            fetched_at=datetime.now(timezone.utc),
        ),
        title=title,
        authors=authors,
        keywords=[],
        abstract=abstract,
        front_matter_paragraphs=front_matter,
        sections=sections,
        stats=ArxivHtmlStats(html_chars=len(html), blocks=blocks),
    )


