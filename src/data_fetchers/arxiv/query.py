"""
arXiv API 查询构建器

构建 arXiv API 查询 URL，支持按分类和按 ID 查询。

arXiv API 文档: https://info.arxiv.org/help/api/user-manual.html
"""

from urllib.parse import urlencode

# arXiv API 端点
ARXIV_API_ENDPOINT = "http://export.arxiv.org/api/query"


def build_category_query(
    categories: list[str],
    max_results: int = 100,
    start: int = 0,
    sort_by: str = "submittedDate",
    sort_order: str = "descending",
) -> str:
    """
    构建按分类查询的 URL

    Args:
        categories: 分类列表，如 ["cs.AI", "cs.CL"]
        max_results: 最大返回数
        start: 起始索引
        sort_by: 排序字段 (submittedDate/lastUpdatedDate/relevance)
        sort_order: 排序顺序 (ascending/descending)

    Returns:
        完整的 API URL

    Example:
        >>> url = build_category_query(["cs.AI", "cs.CL"], max_results=50)
        >>> # http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL&...
    """
    # 构建分类查询：cat:cs.AI OR cat:cs.CL
    if len(categories) == 1:
        search_query = f"cat:{categories[0]}"
    else:
        category_queries = [f"cat:{cat}" for cat in categories]
        search_query = " OR ".join(category_queries)

    params = {
        "search_query": search_query,
        "start": start,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }

    return f"{ARXIV_API_ENDPOINT}?{urlencode(params)}"


def build_single_category_query(
    category: str,
    max_results: int = 100,
    start: int = 0,
    sort_by: str = "submittedDate",
    sort_order: str = "descending",
) -> str:
    """
    构建单个分类查询的 URL

    Args:
        category: 单个分类，如 "cs.AI"
        max_results: 最大返回数
        start: 起始索引
        sort_by: 排序字段
        sort_order: 排序顺序

    Returns:
        完整的 API URL
    """
    return build_category_query(
        categories=[category],
        max_results=max_results,
        start=start,
        sort_by=sort_by,
        sort_order=sort_order,
    )


def build_id_query(paper_ids: list[str]) -> str:
    """
    构建按论文 ID 查询的 URL

    Args:
        paper_ids: 论文 ID 列表，如 ["2501.12345", "2501.12346"]

    Returns:
        完整的 API URL

    Example:
        >>> url = build_id_query(["2501.12345", "2501.12346"])
        >>> # http://export.arxiv.org/api/query?id_list=2501.12345,2501.12346
    """
    id_list = ",".join(paper_ids)
    params = {"id_list": id_list}
    return f"{ARXIV_API_ENDPOINT}?{urlencode(params)}"

