"""
ReAct Agent 执行器

支持普通 LLM 和 DeepSeek Reasoner 的 ReAct Agent 执行。
对于 DeepSeek Reasoner，使用直接 HTTP 调用以正确处理 reasoning_content 字段。
"""

import json
import logging
from typing import Any, Optional, Sequence

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool

from src.llm.deepseek_reasoner import (
    is_deepseek_reasoner,
    execute_deepseek_reasoner_agent,
)

logger = logging.getLogger(__name__)

# 最大工具调用轮数
MAX_TOOL_ITERATIONS = 10


async def execute_react_agent(
    llm: Any,
    tools: Sequence[BaseTool],
    messages: list[BaseMessage],
    max_iterations: int = MAX_TOOL_ITERATIONS,
    # DeepSeek Reasoner 特定参数
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> dict[str, list[BaseMessage]]:
    """
    执行 ReAct Agent

    自动检测是否使用 DeepSeek Reasoner，并选择合适的执行方式。

    Args:
        llm: LangChain Chat 模型实例
        tools: 工具列表
        messages: 初始消息列表
        max_iterations: 最大工具调用迭代次数
        api_key: DeepSeek API Key (用于 Reasoner 模式)
        model: 模型名称 (用于检测 Reasoner 模式)

    Returns:
        包含 "messages" 键的字典，值为完整的消息历史
    """
    # 检查是否为 DeepSeek Reasoner
    if model and is_deepseek_reasoner(model) and api_key:
        logger.info("使用 DeepSeek Reasoner 直接 HTTP 模式")
        return await execute_deepseek_reasoner_agent(
            api_key=api_key,
            model=model,
            tools=tools,
            messages=messages,
            max_iterations=max_iterations,
        )

    # 使用标准 LangChain 执行
    return await _execute_standard_react(llm, tools, messages, max_iterations)


async def _execute_standard_react(
    llm: Any,
    tools: Sequence[BaseTool],
    messages: list[BaseMessage],
    max_iterations: int,
) -> dict[str, list[BaseMessage]]:
    """
    标准 LangChain ReAct 执行

    用于非 DeepSeek Reasoner 的模型。
    """
    # 绑定工具到 LLM
    llm_with_tools = llm.bind_tools(tools)

    # 创建工具名称到工具的映射
    tool_map = {tool.name: tool for tool in tools}

    # 消息历史
    all_messages = list(messages)

    for iteration in range(max_iterations):
        logger.debug(f"ReAct 迭代 {iteration + 1}/{max_iterations}")

        # 调用 LLM
        try:
            response: AIMessage = await llm_with_tools.ainvoke(all_messages)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            error_msg = AIMessage(content=f"调用失败: {e}")
            all_messages.append(error_msg)
            break

        # 添加 AI 响应到消息历史
        all_messages.append(response)

        # 检查是否有工具调用
        if not response.tool_calls:
            logger.debug("无工具调用，ReAct 完成")
            break

        # 执行工具调用
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            logger.debug(f"执行工具: {tool_name}, 参数: {tool_args}")

            if tool_name in tool_map:
                tool = tool_map[tool_name]
                try:
                    if hasattr(tool, "ainvoke"):
                        result = await tool.ainvoke(tool_args)
                    else:
                        result = tool.invoke(tool_args)

                    if not isinstance(result, str):
                        result = json.dumps(result, ensure_ascii=False)

                except Exception as e:
                    logger.warning(f"工具执行失败: {tool_name}, 错误: {e}")
                    result = f"工具执行错误: {e}"
            else:
                logger.warning(f"未知工具: {tool_name}")
                result = f"未知工具: {tool_name}"

            tool_message = ToolMessage(
                content=result,
                tool_call_id=tool_call_id,
                name=tool_name,
            )
            all_messages.append(tool_message)

    return {"messages": all_messages}


def extract_final_response(messages: list[BaseMessage]) -> str:
    """
    从消息历史中提取最终响应

    Args:
        messages: 消息列表

    Returns:
        最终的 AI 响应文本
    """
    # 从后向前查找最后一个有内容且没有工具调用的 AIMessage
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            if msg.content and not msg.tool_calls:
                return str(msg.content)
            # 即使有工具调用，如果有内容也可以使用
            if msg.content:
                return str(msg.content)

    return ""
