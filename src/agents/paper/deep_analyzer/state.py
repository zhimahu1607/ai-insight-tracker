"""
深度分析状态定义

使用 LangGraph 的 TypedDict 状态管理机制，定义 Multi-Agent 工作流的共享状态。
"""

from datetime import datetime
from typing import Annotated, Literal, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class DeepAnalysisState(TypedDict, total=False):
    """
    深度分析工作流状态

    所有 Agent 节点共享同一个状态对象，通过状态字段传递信息。
    使用 total=False 使所有字段都是可选的，便于部分更新。

    状态字段分为五类：
    1. 输入字段：论文基本信息
    2. 论文全文字段：arXiv 官方 HTML 全文解析后的内容
    3. Supervisor 状态：消息历史和研究计划
    4. 研究与写作状态：研究笔记、草稿、反馈
    5. 流程控制：迭代次数和时间戳
    """

    # === 输入字段 ===
    paper_id: str  # arXiv 论文 ID
    paper_title: str  # 论文标题
    paper_abstract: str  # 论文摘要
    paper_html_url: str  # arXiv 官方 HTML 全文链接
    requirements: Optional[str]  # 用户指定的分析需求 (来自 Issue Body)

    # === 论文全文字段 (新增) ===
    paper_full_content: Optional[str]  # 论文全文概要 (给 Writer 使用)
    paper_tables_content: Optional[str]  # 表格内容概要
    paper_figures_content: Optional[str]  # 图表说明概要
    paper_sections_available: bool  # 是否有章节内容可查询
    paper_total_sections: int  # 论文章节总数（含子章节）
    paper_references_count: int  # 参考文献数量
    fulltext_parse_status: str  # 全文解析状态: success / failed / pending

    # === Supervisor 状态 ===
    supervisor_messages: Annotated[list[BaseMessage], add_messages]  # Supervisor 消息历史
    research_plan: Optional[str]  # 当前研究计划

    # === 研究与写作状态 ===
    research_notes: list[str]  # 压缩后的研究笔记 (每轮研究添加一条)
    raw_research: list[str]  # 原始搜索结果 (用于调试)
    current_research_topic: Optional[str]  # 当前研究主题 (从 Supervisor 传递)
    draft_report: Optional[str]  # 当前草稿报告
    review_feedback: Optional[str]  # Reviewer 的修改建议
    final_report: Optional[str]  # 最终通过的报告

    # === 流程控制 ===
    research_iterations: int  # 当前研究迭代次数
    max_iterations: int  # 最大研究迭代次数
    write_iterations: int  # 写作修改次数
    max_write_iterations: int  # 最大写作修改次数
    analysis_started_at: Optional[datetime]  # 分析开始时间
    next_action: Optional[Literal["research", "write", "end"]]  # 下一步动作


def create_initial_state(
    paper_id: str,
    paper_title: str,
    paper_abstract: str,
    paper_html_url: str,
    requirements: Optional[str] = None,
    max_iterations: int = 5,
    max_write_iterations: int = 3,
    # 论文全文相关参数 (新增)
    paper_full_content: Optional[str] = None,
    paper_tables_content: Optional[str] = None,
    paper_figures_content: Optional[str] = None,
    paper_sections_available: bool = False,
    paper_total_sections: int = 0,
    paper_references_count: int = 0,
    fulltext_parse_status: str = "pending",
) -> DeepAnalysisState:
    """
    创建初始状态

    Args:
        paper_id: arXiv 论文 ID
        paper_title: 论文标题
        paper_abstract: 论文摘要
        paper_html_url: arXiv 官方 HTML 全文链接
        requirements: 用户指定的分析需求
        max_iterations: 最大研究迭代次数
        max_write_iterations: 最大写作修改次数
        paper_full_content: 论文全文概要
        paper_tables_content: 表格内容概要
        paper_figures_content: 图表说明概要
        paper_sections_available: 是否有章节内容可查询
        paper_total_sections: 论文章节总数（含子章节）
        paper_references_count: 参考文献数量
        fulltext_parse_status: 全文解析状态

    Returns:
        初始化的 DeepAnalysisState
    """
    return DeepAnalysisState(
        # 输入字段
        paper_id=paper_id,
        paper_title=paper_title,
        paper_abstract=paper_abstract,
        paper_html_url=paper_html_url,
        requirements=requirements,
        # 论文全文字段
        paper_full_content=paper_full_content,
        paper_tables_content=paper_tables_content,
        paper_figures_content=paper_figures_content,
        paper_sections_available=paper_sections_available,
        paper_total_sections=paper_total_sections,
        paper_references_count=paper_references_count,
        fulltext_parse_status=fulltext_parse_status,
        # Supervisor 状态
        supervisor_messages=[],
        research_plan=None,
        # 研究与写作状态
        research_notes=[],
        raw_research=[],
        current_research_topic=None,
        draft_report=None,
        review_feedback=None,
        final_report=None,
        # 流程控制
        research_iterations=0,
        max_iterations=max_iterations,
        write_iterations=0,
        max_write_iterations=max_write_iterations,
        analysis_started_at=None,
        next_action=None,
    )
