"""
深度分析 LangGraph 工作流

使用 StateGraph 构建 Multi-Agent 工作流图。
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, START, END

from .state import DeepAnalysisState
from .nodes import (
    supervisor_node,
    supervisor_tools_node,
    route_supervisor_tools,
    researcher_node,
    writer_node,
    reviewer_node,
    route_reviewer,
)


logger = logging.getLogger(__name__)


def should_continue_research(state: DeepAnalysisState) -> Literal["supervisor", "__end__"]:
    """
    判断是否继续研究迭代

    Args:
        state: 当前状态

    Returns:
        下一个节点或结束
    """
    iterations = state.get("research_iterations", 0)
    max_iterations = state.get("max_iterations", 5)

    if iterations >= max_iterations:
        logger.info(f"达到最大研究迭代次数 ({max_iterations})，进入写作阶段")
        return "__end__"

    return "supervisor"


def build_deep_analysis_graph() -> StateGraph:
    """
    构建深度分析工作流图

    工作流结构:
    ```
    START → supervisor → supervisor_tools → [researcher | writer]
                 ↑                              ↓
                 └──────────────────────────────┘

    writer → reviewer → [writer | END]
    ```

    Returns:
        编译后的 StateGraph
    """
    # 创建状态图
    graph = StateGraph(DeepAnalysisState)

    # ============================================================
    # 添加节点
    # ============================================================

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("supervisor_tools", supervisor_tools_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)
    graph.add_node("reviewer", reviewer_node)

    # ============================================================
    # 添加边
    # ============================================================

    # 入口: START → supervisor
    graph.add_edge(START, "supervisor")

    # supervisor → supervisor_tools
    graph.add_edge("supervisor", "supervisor_tools")

    # supervisor_tools → [researcher | writer] (条件边)
    graph.add_conditional_edges(
        "supervisor_tools",
        route_supervisor_tools,
        {
            "researcher": "researcher",
            "writer": "writer",
        },
    )

    # researcher → supervisor (返回评估)
    graph.add_edge("researcher", "supervisor")

    # writer → reviewer
    graph.add_edge("writer", "reviewer")

    # reviewer → [writer | END] (条件边)
    graph.add_conditional_edges(
        "reviewer",
        route_reviewer,
        {
            "writer": "writer",
            "__end__": END,
        },
    )

    return graph


# 全局编译的工作流图（惰性初始化）
_compiled_graph = None


def get_compiled_graph():
    """
    获取编译后的工作流图（单例）

    Returns:
        编译后的 CompiledStateGraph
    """
    global _compiled_graph
    if _compiled_graph is None:
        graph = build_deep_analysis_graph()
        _compiled_graph = graph.compile()
        logger.info("深度分析工作流图已编译")
    return _compiled_graph
