"""
DeepSeek Reasoner 工具调用适配器

DeepSeek reasoner 模型在工具调用时需要特殊处理 reasoning_content 字段。
根据官方文档: https://api-docs.deepseek.com/zh-cn/guides/tool_calls

由于 LangChain 和 OpenAI SDK 不支持 reasoning_content 字段，
本模块直接使用 httpx 调用 DeepSeek API。

注意：deepseek-reasoner 的工具调用需要使用 beta 端点：
https://api.deepseek.com/beta
"""

import json
import logging
from typing import Any, Optional, List, Sequence

import httpx
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# DeepSeek Reasoner 工具调用专用 Beta 端点
DEEPSEEK_BETA_BASE_URL = "https://api.deepseek.com/beta"


def is_deepseek_reasoner(model: str) -> bool:
    """检查是否为 DeepSeek reasoner 模型"""
    model_lower = model.lower()
    return "reasoner" in model_lower or "r1" in model_lower


class DeepSeekReasonerClient:
    """
    DeepSeek Reasoner 直接 HTTP 客户端

    直接使用 httpx 调用 DeepSeek API，完全控制 reasoning_content 字段的处理。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-reasoner",
        base_url: str = DEEPSEEK_BETA_BASE_URL,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: float = 300.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def _message_to_dict(self, msg: BaseMessage) -> dict[str, Any]:
        """将 LangChain 消息转换为 API 格式"""
        if isinstance(msg, SystemMessage):
            return {"role": "system", "content": str(msg.content)}
        elif isinstance(msg, HumanMessage):
            return {"role": "user", "content": str(msg.content)}
        elif isinstance(msg, AIMessage):
            result: dict[str, Any] = {"role": "assistant"}

            # 添加内容
            if msg.content:
                result["content"] = str(msg.content)
            else:
                result["content"] = ""

            # 添加 reasoning_content（DeepSeek Reasoner 必需）
            reasoning_content = msg.additional_kwargs.get("reasoning_content")
            if reasoning_content:
                result["reasoning_content"] = reasoning_content

            # 添加工具调用
            if msg.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["args"], ensure_ascii=False),
                        },
                    }
                    for tc in msg.tool_calls
                ]

            return result
        elif isinstance(msg, ToolMessage):
            return {
                "role": "tool",
                "tool_call_id": msg.tool_call_id,
                "content": str(msg.content),
            }
        else:
            raise ValueError(f"不支持的消息类型: {type(msg)}")

    def _dict_to_message(self, data: dict[str, Any]) -> AIMessage:
        """将 API 响应转换为 LangChain AIMessage"""
        content = data.get("content", "") or ""
        reasoning_content = data.get("reasoning_content")
        tool_calls_data = data.get("tool_calls", [])

        # 转换工具调用格式
        tool_calls = []
        if tool_calls_data:
            for tc in tool_calls_data:
                func = tc.get("function", {})
                args_str = func.get("arguments", "{}")
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}

                tool_calls.append(
                    {
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "args": args,
                    }
                )

        # 构建 AIMessage
        additional_kwargs: dict[str, Any] = {}
        if reasoning_content:
            additional_kwargs["reasoning_content"] = reasoning_content

        return AIMessage(
            content=content,
            tool_calls=tool_calls,
            additional_kwargs=additional_kwargs,
        )

    def _tools_to_schema(self, tools: Sequence[BaseTool]) -> list[dict[str, Any]]:
        """将 LangChain 工具转换为 API 工具格式"""
        tool_schemas = []
        for tool in tools:
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                },
            }

            # 获取参数 schema
            if hasattr(tool, "args_schema") and tool.args_schema:
                args_schema = tool.args_schema.model_json_schema()
                # 移除不需要的字段
                args_schema.pop("title", None)
                args_schema.pop("description", None)
                schema["function"]["parameters"] = args_schema
            else:
                schema["function"]["parameters"] = {
                    "type": "object",
                    "properties": {},
                }

            tool_schemas.append(schema)

        return tool_schemas

    async def chat(
        self,
        messages: list[BaseMessage],
        tools: Optional[Sequence[BaseTool]] = None,
    ) -> AIMessage:
        """
        异步聊天调用

        Args:
            messages: LangChain 消息列表
            tools: 可选的工具列表

        Returns:
            AIMessage 响应
        """
        # 构建请求体
        request_body: dict[str, Any] = {
            "model": self.model,
            "messages": [self._message_to_dict(msg) for msg in messages],
            "temperature": self.temperature,
        }

        if self.max_tokens:
            request_body["max_tokens"] = self.max_tokens

        if tools:
            request_body["tools"] = self._tools_to_schema(tools)

        # 发送请求
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"DeepSeek API 错误: {response.status_code} - {error_text}")
                raise RuntimeError(
                    f"DeepSeek API 错误: {response.status_code} - {error_text}"
                )

            result = response.json()

        # 解析响应
        choices = result.get("choices", [])
        if not choices:
            raise RuntimeError("DeepSeek API 返回空响应")

        message_data = choices[0].get("message", {})
        return self._dict_to_message(message_data)


async def execute_deepseek_reasoner_agent(
    api_key: str,
    model: str,
    tools: Sequence[BaseTool],
    messages: list[BaseMessage],
    max_iterations: int = 10,
    temperature: float = 0.7,
    timeout: float = 300.0,
) -> dict[str, list[BaseMessage]]:
    """
    执行 DeepSeek Reasoner ReAct Agent

    使用直接 HTTP 调用，确保 reasoning_content 被正确处理。

    Args:
        api_key: DeepSeek API Key
        model: 模型名称
        tools: 工具列表
        messages: 初始消息列表
        max_iterations: 最大迭代次数
        temperature: 温度参数
        timeout: 请求超时

    Returns:
        包含 "messages" 键的字典
    """
    client = DeepSeekReasonerClient(
        api_key=api_key,
        model=model,
        temperature=temperature,
        timeout=timeout,
    )

    # 创建工具名称到工具的映射
    tool_map = {tool.name: tool for tool in tools}

    # 消息历史
    all_messages = list(messages)

    for iteration in range(max_iterations):
        logger.debug(f"DeepSeek Reasoner 迭代 {iteration + 1}/{max_iterations}")

        try:
            response = await client.chat(all_messages, tools)
        except Exception as e:
            logger.error(f"DeepSeek Reasoner 调用失败: {e}")
            error_msg = AIMessage(content=f"调用失败: {e}")
            all_messages.append(error_msg)
            break

        # 检查 reasoning_content
        reasoning_content = response.additional_kwargs.get("reasoning_content")
        if reasoning_content:
            logger.debug(
                f"响应包含 reasoning_content (长度: {len(reasoning_content)})"
            )

        # 添加响应到消息历史
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

            logger.debug(f"执行工具: {tool_name}")

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


def create_deepseek_client(
    model: str,
    api_key: str,
    base_url: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    timeout: Optional[float] = None,
    max_retries: int = 3,
) -> ChatOpenAI:
    """
    创建 DeepSeek 客户端

    注意：对于 reasoner 模型的工具调用，应使用 execute_deepseek_reasoner_agent 函数，
    而不是这个返回的 LangChain 客户端。此客户端主要用于非工具调用场景。

    Args:
        model: 模型名称
        api_key: API Key
        base_url: API Base URL
        temperature: 温度参数
        max_tokens: 最大 token 数
        timeout: 超时时间
        max_retries: 最大重试次数

    Returns:
        ChatOpenAI 实例
    """
    # 对于 reasoner 模型，使用 beta 端点
    if is_deepseek_reasoner(model):
        actual_base_url = DEEPSEEK_BETA_BASE_URL
        logger.info(
            f"使用 DeepSeek Reasoner: {model}, 端点: {actual_base_url}"
        )
    else:
        actual_base_url = base_url
        logger.debug(f"使用 DeepSeek: {model}")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=actual_base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
    )
