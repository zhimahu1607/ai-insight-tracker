"""
Supervisor Agent 节点

负责研究规划、任务分配和进度评估。
使用 LangGraph ToolNode 简化工具调用处理。
"""

import logging
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from src.llm import LLMClient
from src.prompts.prompt_loader import PromptLoader
from ..state import DeepAnalysisState


logger = logging.getLogger(__name__)


# ============================================================
# Supervisor 工具定义
# ============================================================


class ConductResearchInput(BaseModel):
    """研究任务输入"""

    topic: str = Field(description="需要研究的具体主题或问题")


class ResearchCompleteInput(BaseModel):
    """研究完成输入"""

    summary: str = Field(description="研究阶段的总结")


@tool(args_schema=ConductResearchInput)
def conduct_research(topic: str) -> str:
    """
    分配研究任务给 Researcher Agent。

    当需要收集更多信息时调用此工具。

    Args:
        topic: 需要研究的具体主题或问题

    Returns:
        确认信息
    """
    return f"已安排研究任务: {topic}"


@tool(args_schema=ResearchCompleteInput)
def research_complete(summary: str) -> str:
    """
    标记研究完成，进入写作阶段。

    当收集了足够的信息后调用此工具。

    Args:
        summary: 研究阶段的总结

    Returns:
        确认信息
    """
    return f"研究完成，准备进入写作阶段"


SUPERVISOR_TOOLS = [conduct_research, research_complete]

# 创建 ToolNode 实例
supervisor_tool_node = ToolNode(SUPERVISOR_TOOLS)


# ============================================================
# Supervisor 节点
# ============================================================


def _load_supervisor_prompt() -> str:
    """加载 Supervisor Prompt 模板"""
    return PromptLoader.load("paper", "deep_analyzer", "supervisor")


async def supervisor_node(state: DeepAnalysisState) -> dict:
    """
    Supervisor 决策节点

    分析当前研究进度和收集的信息，决定下一步行动。

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典，包含 supervisor_messages
    """
    # 加载 Prompt
    system_prompt = _load_supervisor_prompt()

    # 构建当前状态描述
    status_parts = [
        f"论文 ID: {state.get('paper_id', '')}",
        f"论文标题: {state.get('paper_title', '')}",
        f"论文摘要:\n{state.get('paper_abstract', '')}",
    ]

    if state.get("requirements"):
        status_parts.append(f"\n用户分析需求: {state['requirements']}")

    if state.get("research_notes"):
        notes = "\n".join(
            f"[研究 {i+1}] {note}"
            for i, note in enumerate(state["research_notes"])
        )
        status_parts.append(f"\n已收集的研究笔记:\n{notes}")

    status_parts.append(
        f"\n当前研究迭代: {state.get('research_iterations', 0)}/{state.get('max_iterations', 5)}"
    )

    current_status = "\n".join(status_parts)

    # 获取消息历史
    messages = list(state.get("supervisor_messages", []))

    # 如果是首次调用，添加初始任务消息
    if not messages:
        messages.append(
            HumanMessage(content=f"请分析以下论文并制定研究计划:\n\n{current_status}")
        )
    else:
        # 如果有研究笔记更新，添加更新消息
        if state.get("research_notes"):
            last_note = state["research_notes"][-1]
            messages.append(
                HumanMessage(
                    content=f"研究完成。收集到的信息:\n{last_note}\n\n当前状态:\n{current_status}\n\n请决定下一步：继续研究还是开始写作？"
                )
            )

    # 调用 LLM
    async with LLMClient(temperature=0.3) as llm_client:
        langchain_llm = llm_client.get_langchain_client()
        llm_with_tools = langchain_llm.bind_tools(SUPERVISOR_TOOLS)

        response = await llm_with_tools.ainvoke(
            [SystemMessage(content=system_prompt)] + messages
        )

    return {"supervisor_messages": [response]}


async def supervisor_tools_node(state: DeepAnalysisState) -> dict:
    """
    Supervisor 工具执行节点

    使用 ToolNode 执行工具调用，解析结果更新状态。

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    messages = state.get("supervisor_messages", [])
    if not messages:
        return {}

    last_message = messages[-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {}

    # 使用 ToolNode 执行工具
    tool_result = await supervisor_tool_node.ainvoke({"messages": [last_message]})
    tool_messages = tool_result.get("messages", [])

    # 解析工具调用结果，更新路由状态
    next_action = None
    current_topic = None

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        if tool_name == "conduct_research":
            topic = tool_args.get("topic", "")
            next_action = "research"
            current_topic = topic
            logger.info(f"Supervisor 分配研究任务: {topic}")
        elif tool_name == "research_complete":
            summary = tool_args.get("summary", "")
            next_action = "write"
            logger.info(f"Supervisor 完成研究: {summary[:100]}...")

    return {
        "supervisor_messages": tool_messages,
        "next_action": next_action,
        "current_research_topic": current_topic,
    }


def route_supervisor_tools(state: DeepAnalysisState) -> Literal["researcher", "writer"]:
    """
    根据 Supervisor 工具调用结果决定路由

    Args:
        state: 当前工作流状态

    Returns:
        下一个节点名称
    """
    next_action = state.get("next_action")

    if next_action == "research":
        return "researcher"
    elif next_action == "write":
        return "writer"
    else:
        # 默认继续研究
        return "researcher"
