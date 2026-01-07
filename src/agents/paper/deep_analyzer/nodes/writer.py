"""
Writer Agent 节点

负责撰写深度分析报告。
"""

import logging

from langchain_core.messages import SystemMessage, HumanMessage

from src.llm import LLMClient
from src.agents.prompt_loader import PromptLoader
from ..state import DeepAnalysisState


logger = logging.getLogger(__name__)


def _load_writer_prompt() -> str:
    """加载 Writer Prompt 模板"""
    return PromptLoader.load("paper", "deep_analyzer", "writer")


async def writer_node(state: DeepAnalysisState) -> dict:
    """
    Writer 撰写节点

    基于研究笔记撰写深度分析报告。

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典，包含 draft_report 和 write_iterations
    """
    # 加载 Prompt
    system_prompt = _load_writer_prompt()

    # 构建写作任务
    research_notes = state.get("research_notes", [])
    notes_text = "\n\n---\n\n".join(
        f"### 研究笔记 {i+1}\n{note}"
        for i, note in enumerate(research_notes)
    )

    task_parts = [
        f"请基于以下信息撰写深度分析报告：",
        f"\n## 论文信息",
        f"- ID: {state.get('paper_id', '')}",
        f"- 标题: {state.get('paper_title', '')}",
        f"- 摘要: {state.get('paper_abstract', '')}",
    ]

    # 添加论文全文内容（如果有）
    if state.get("paper_full_content"):
        task_parts.append(f"\n## 论文全文概要\n{state['paper_full_content']}")

    # 添加表格内容（如果有）
    if state.get("paper_tables_content"):
        task_parts.append(f"\n## 论文表格\n{state['paper_tables_content']}")

    # 添加图表说明（如果有）
    if state.get("paper_figures_content"):
        task_parts.append(f"\n## 论文图表\n{state['paper_figures_content']}")

    if state.get("requirements"):
        task_parts.append(f"\n## 用户需求\n{state['requirements']}")

    task_parts.append(f"\n## 研究笔记\n{notes_text}")

    # 如果有 Reviewer 反馈，添加修改要求
    if state.get("review_feedback"):
        task_parts.append(f"\n## Reviewer 修改建议\n{state['review_feedback']}")
        task_parts.append("\n请根据以上修改建议，修改当前草稿：")
        if state.get("draft_report"):
            task_parts.append(f"\n## 当前草稿\n{state['draft_report']}")

    task = "\n".join(task_parts)

    logger.info(f"Writer 开始撰写报告 (第 {state.get('write_iterations', 0) + 1} 次)")

    try:
        # 调用 LLM
        async with LLMClient(temperature=0.5) as llm_client:
            report = await llm_client.chat(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=task),
                ]
            )

        logger.info(f"Writer 完成报告撰写，长度: {len(report)} 字符")

    except Exception as e:
        logger.error(f"Writer 撰写失败: {e}")
        report = f"# 报告生成失败\n\n错误: {e}"

    return {
        "draft_report": report,
        "write_iterations": state.get("write_iterations", 0) + 1,
        "review_feedback": None,  # 清除之前的反馈
    }
