"""
arXiv 论文加载工具

异步获取 arXiv 论文的详细信息。
"""

import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Optional

import aiohttp
from langchain_core.tools import tool
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

# arXiv API 配置
ARXIV_API_URL = "http://export.arxiv.org/api/query"
ARXIV_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivLoaderInput(BaseModel):
    """arXiv 加载工具输入"""

    paper_id: str = Field(description="arXiv 论文 ID，如 '2501.12345' 或 '2501.12345v1'")


async def load_arxiv(paper_id: str, timeout: float = 30.0) -> str:
    """
    获取 arXiv 论文详细信息

    Args:
        paper_id: arXiv 论文 ID
        timeout: 请求超时(秒)

    Returns:
        格式化的论文信息字符串
    """
    # 清理 ID 格式
    paper_id = paper_id.strip()
    if paper_id.startswith("arXiv:"):
        paper_id = paper_id[6:]

    # 构建查询 URL
    query_url = f"{ARXIV_API_URL}?id_list={paper_id}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(query_url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status != 200:
                    return f"获取论文失败: HTTP {response.status}"
                
                xml_content = await response.text()

        # 解析 XML
        root = ET.fromstring(xml_content)
        
        # 查找 entry
        entry = root.find("atom:entry", ARXIV_NAMESPACE)
        if entry is None:
            return f"未找到论文: {paper_id}"

        # 提取信息
        title = entry.find("atom:title", ARXIV_NAMESPACE)
        title_text = title.text.strip().replace("\n", " ") if title is not None and title.text else "无标题"

        summary = entry.find("atom:summary", ARXIV_NAMESPACE)
        summary_text = summary.text.strip() if summary is not None and summary.text else "无摘要"

        # 提取作者
        authors = entry.findall("atom:author", ARXIV_NAMESPACE)
        author_names = []
        for author in authors:
            name = author.find("atom:name", ARXIV_NAMESPACE)
            if name is not None and name.text:
                author_names.append(name.text)
        authors_text = ", ".join(author_names) if author_names else "未知作者"

        # 提取分类
        categories = entry.findall("atom:category", ARXIV_NAMESPACE)
        category_terms = [cat.get("term", "") for cat in categories if cat.get("term")]
        categories_text = ", ".join(category_terms) if category_terms else "未分类"

        # 提取链接
        pdf_link = ""
        abs_link = ""
        for link in entry.findall("atom:link", ARXIV_NAMESPACE):
            href = link.get("href", "")
            title_attr = link.get("title", "")
            if title_attr == "pdf":
                pdf_link = href
            elif link.get("rel") == "alternate":
                abs_link = href

        # 提取发布时间
        published = entry.find("atom:published", ARXIV_NAMESPACE)
        published_text = published.text[:10] if published is not None and published.text else "未知"

        # 提取评论（如会议信息）
        comment = entry.find("{http://arxiv.org/schemas/atom}comment")
        comment_text = comment.text.strip() if comment is not None and comment.text else None

        # 格式化输出
        result = f"""论文 ID: {paper_id}
标题: {title_text}
作者: {authors_text}
分类: {categories_text}
发布日期: {published_text}
摘要页: {abs_link}
PDF: {pdf_link}
"""
        if comment_text:
            result += f"备注: {comment_text}\n"

        result += f"\n摘要:\n{summary_text}"

        return result

    except asyncio.TimeoutError:
        logger.warning(f"arXiv API 超时: {paper_id}")
        return f"获取论文超时: {paper_id}"
    except aiohttp.ClientError as e:
        logger.warning(f"arXiv API 请求失败: {e}")
        return f"获取论文失败: {e}"
    except ET.ParseError as e:
        logger.warning(f"arXiv XML 解析失败: {e}")
        return f"解析论文信息失败: {e}"
    except Exception as e:
        logger.error(f"获取 arXiv 论文异常: {e}")
        return f"获取论文异常: {e}"


def get_arxiv_tool():
    """
    获取 LangChain 工具实例

    Returns:
        绑定了 arXiv 加载功能的 LangChain Tool
    """

    @tool(args_schema=ArxivLoaderInput)
    async def arxiv_loader(paper_id: str) -> str:
        """
        获取 arXiv 论文的详细信息。

        用于：
        - 验证论文信息
        - 获取完整摘要和作者列表
        - 查看论文分类和会议信息

        Args:
            paper_id: arXiv 论文 ID，如 '2501.12345'

        Returns:
            格式化的论文详细信息
        """
        return await load_arxiv(paper_id)

    return arxiv_loader
