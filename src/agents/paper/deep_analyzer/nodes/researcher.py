"""
Researcher Agent 节点

负责执行具体的信息搜索和论文分析任务。
使用自定义 ReAct 执行器，支持 DeepSeek reasoner 的 reasoning_content 字段。
支持论文全文内容查询（当 PDF 解析成功时）。
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import LLMClient
from src.agents.prompt_loader import PromptLoader
from ..state import DeepAnalysisState
from ..tools import get_search_tool, get_paper_reader_tool
from ..tools.arxiv_loader import get_arxiv_tool
from ..tools.react_executor import execute_react_agent, extract_final_response


logger = logging.getLogger(__name__)


def _load_researcher_prompt() -> str:
    """加载 Researcher Prompt 模板"""
    return PromptLoader.load("paper", "deep_analyzer", "researcher")


async def researcher_node(state: DeepAnalysisState) -> dict:
    """
    Researcher 执行节点

    根据 Supervisor 分配的主题执行研究任务。

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典，包含 research_notes 和 research_iterations
    """
    # 获取当前研究主题
    topic = state.get("current_research_topic", "")
    if not topic:
        logger.warning("Researcher: 未收到研究主题")
        return {
            "research_notes": state.get("research_notes", []) + ["未指定研究主题"],
            "research_iterations": state.get("research_iterations", 0) + 1,
        }

    logger.info(f"Researcher 开始研究: {topic}")

    # 加载 Prompt
    system_prompt = _load_researcher_prompt()

    # 构建任务描述
    task_parts = [
        f"请研究以下主题:",
        f"",
        f"**研究主题**: {topic}",
        f"",
        f"**论文上下文**:",
        f"- 论文 ID: {state.get('paper_id', '')}",
        f"- 论文标题: {state.get('paper_title', '')}",
        f"- 论文摘要: {state.get('paper_abstract', '')[:500]}...",
    ]

    # 如果有论文全文可用，添加提示
    if state.get("paper_sections_available"):
        task_parts.extend([
            f"",
            f"**注意**: 论文全文已加载（共 {state.get('paper_total_pages', 0)} 页）。",
            f"你可以使用 paper_reader 工具查询论文的具体章节内容或搜索关键词。",
        ])

    task_parts.append("")
    task_parts.append("请使用工具收集信息，然后输出研究笔记。")
    task = "\n".join(task_parts)

    # 创建工具
    tools = [get_search_tool(), get_arxiv_tool()]

    # 如果论文全文可用，添加 paper_reader 工具
    if state.get("paper_sections_available"):
        tools.append(get_paper_reader_tool())

    try:
        # 创建 LLM 客户端
        async with LLMClient(temperature=0.3) as llm_client:
            langchain_llm = llm_client.get_langchain_client()

            # 使用自定义 ReAct 执行器（支持 DeepSeek reasoner）
            # 传递 api_key 和 model 以便检测是否使用 Reasoner 模式
            result = await execute_react_agent(
                llm=langchain_llm,
                tools=tools,
                messages=[
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=task),
                ],
                max_iterations=10,
                api_key=llm_client._api_key,  # 传递 API Key
                model=llm_client.model,  # 传递模型名称
            )

            # 提取最终响应
            messages = result.get("messages", [])
            final_response = extract_final_response(messages)

            if not final_response:
                final_response = f"研究主题: {topic}\n\n未能获取有效信息。"

            # 压缩研究笔记（如果太长）
            if len(final_response) > 1500:
                compress_prompt = f"""请将以下研究笔记压缩到 500 字以内，保留关键信息：

{final_response}"""
                compressed = await llm_client.chat(
                    [HumanMessage(content=compress_prompt)]
                )
                final_response = compressed

        logger.info(f"Researcher 完成研究: {topic[:50]}...")

    except Exception as e:
        logger.error(f"Researcher 研究失败: {e}")
        final_response = f"研究主题: {topic}\n\n研究过程中发生错误: {e}"

    # 更新状态
    current_notes = list(state.get("research_notes", []))
    current_notes.append(final_response)

    return {
        "research_notes": current_notes,
        "research_iterations": state.get("research_iterations", 0) + 1,
        "current_research_topic": None,  # 清除当前主题
    }
