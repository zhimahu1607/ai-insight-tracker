"""
Reviewer Agent 节点

负责审核报告质量，提供修改建议或批准报告。
使用 LangGraph ToolNode 简化工具调用处理。
"""

import logging
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from src.llm import LLMClient
from src.agents.prompt_loader import PromptLoader
from ..state import DeepAnalysisState


logger = logging.getLogger(__name__)


# ============================================================
# Reviewer 工具定义
# ============================================================


class ApproveReportInput(BaseModel):
    """批准报告输入"""

    comment: str = Field(default="", description="批准评语（可选）")


class RequestRevisionInput(BaseModel):
    """请求修改输入"""

    feedback: str = Field(description="具体的修改建议")


@tool(args_schema=ApproveReportInput)
def approve_report(comment: str = "") -> str:
    """
    批准报告，结束审核流程。

    当报告质量达标时调用此工具。

    Args:
        comment: 批准评语（可选）

    Returns:
        确认信息
    """
    return f"报告已批准。{comment}"


@tool(args_schema=RequestRevisionInput)
def request_revision(feedback: str) -> str:
    """
    请求修改，返回给 Writer 修改。

    当报告需要改进时调用此工具。

    Args:
        feedback: 具体的修改建议

    Returns:
        确认信息
    """
    return f"已请求修改: {feedback}"


REVIEWER_TOOLS = [approve_report, request_revision]

# 创建 ToolNode 实例
reviewer_tool_node = ToolNode(REVIEWER_TOOLS)


# ============================================================
# Reviewer 节点
# ============================================================


def _load_reviewer_prompt() -> str:
    """加载 Reviewer Prompt 模板"""
    return PromptLoader.load("paper", "deep_analyzer", "reviewer")


async def reviewer_node(state: DeepAnalysisState) -> dict:
    """
    Reviewer 审核节点

    评估报告质量，决定批准或请求修改。

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    # 加载 Prompt
    system_prompt = _load_reviewer_prompt()

    # 获取当前草稿
    draft_report = state.get("draft_report", "")
    if not draft_report:
        logger.warning("Reviewer: 未收到报告草稿")
        return {"final_report": "无报告内容", "next_action": "end"}

    # 构建审核任务
    task = f"""请审核以下深度分析报告：

**论文信息**:
- ID: {state.get('paper_id', '')}
- 标题: {state.get('paper_title', '')}

**当前修改次数**: {state.get('write_iterations', 0)}

**报告内容**:

{draft_report}

请评估报告质量，使用工具表达你的决定：
- 如果质量达标，使用 approve_report
- 如果需要改进，使用 request_revision 并提供具体建议"""

    logger.info(f"Reviewer 开始审核 (第 {state.get('write_iterations', 0)} 版)")

    try:
        # 创建 LLM 客户端
        async with LLMClient(temperature=0.3) as llm_client:
            langchain_llm = llm_client.get_langchain_client()
            llm_with_tools = langchain_llm.bind_tools(REVIEWER_TOOLS)

            response = await llm_with_tools.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=task),
                ]
            )

        # 解析工具调用结果
        result = {}

        if isinstance(response, AIMessage) and response.tool_calls:
            # 使用 ToolNode 执行工具
            tool_result = await reviewer_tool_node.ainvoke({"messages": [response]})

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                if tool_name == "approve_report":
                    comment = tool_args.get("comment", "")
                    logger.info(f"Reviewer 批准报告: {comment}")
                    result["final_report"] = draft_report
                    result["next_action"] = "end"

                elif tool_name == "request_revision":
                    feedback = tool_args.get("feedback", "")
                    logger.info(f"Reviewer 请求修改: {feedback[:100]}...")
                    result["review_feedback"] = feedback
                    result["next_action"] = "write"
        else:
            # 没有工具调用，默认批准
            logger.info("Reviewer 未使用工具，默认批准")
            result["final_report"] = draft_report
            result["next_action"] = "end"

    except Exception as e:
        logger.error(f"Reviewer 审核失败: {e}")
        # 出错时默认批准当前草稿
        result = {
            "final_report": draft_report,
            "next_action": "end",
        }

    return result


def route_reviewer(state: DeepAnalysisState) -> Literal["writer", "__end__"]:
    """
    根据 Reviewer 决定进行路由

    Args:
        state: 当前工作流状态

    Returns:
        下一个节点名称
    """
    next_action = state.get("next_action")
    write_iterations = state.get("write_iterations", 0)
    max_write_iterations = state.get("max_write_iterations", 3)

    # 如果达到最大修改次数，强制结束
    if write_iterations >= max_write_iterations:
        logger.info(f"达到最大修改次数 ({max_write_iterations})，强制结束")
        return "__end__"

    if next_action == "write":
        return "writer"
    else:
        return "__end__"
