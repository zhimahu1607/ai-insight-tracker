"""
浅度分析器泛型基类

提供通用的 LLM 结构化分析逻辑，支持异步批量处理。
具体分析器（Paper/News）继承此基类并实现抽象方法。
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Generic, TypeVar, Optional

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from tqdm.asyncio import tqdm_asyncio

from src.config import get_settings
from src.llm import LLMClient, LLMParseError, LLMRateLimitError
from src.agents.shared import get_llm_semaphore
from src.agents.prompt_loader import PromptLoader


logger = logging.getLogger(__name__)


# 泛型类型变量
TInput = TypeVar("TInput")      # 输入类型 (Paper / NewsItem)
TOutput = TypeVar("TOutput")    # 输出类型 (AnalyzedPaper / AnalyzedNews)
TAnalysis = TypeVar("TAnalysis")  # 分析结果类型 (PaperLightAnalysis / NewsLightAnalysis)


class BaseLightAnalyzer(ABC, Generic[TInput, TOutput, TAnalysis]):
    """
    浅度分析器泛型基类

    使用 LLM 对输入数据进行结构化分析，支持异步批量处理。

    子类需要实现：
    - _get_prompt_key(): 返回 Prompt 加载的 key
    - _build_user_content(): 构建用户消息内容
    - _create_output(): 创建输出对象
    - _get_analysis_schema(): 返回分析结果的 Pydantic 类
    - _set_analysis_result(): 设置分析结果到输出对象
    - _get_item_id(): 获取输入项的 ID（用于日志）
    - _get_progress_desc(): 返回进度条描述
    - _get_progress_unit(): 返回进度条单位

    Attributes:
        llm_client: LLM 客户端实例
        language: 输出语言 (zh/en)

    Usage:
        async with LLMClient() as client:
            analyzer = ConcreteAnalyzer(client)
            results = await analyzer.analyze_batch(items)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        language: Optional[str] = None,
    ):
        """
        初始化浅度分析器

        Args:
            llm_client: LLM 客户端实例
            language: 输出语言，默认从配置系统读取
        """
        self._llm_client = llm_client
        self._semaphore = get_llm_semaphore()

        # 从配置获取默认语言
        settings = get_settings()
        self._language = language or settings.notification.language

        # 加载 Prompt 模板
        self._system_prompt, self._user_prompt = self._load_prompts()

    def _load_prompts(self) -> tuple[str, str]:
        """
        从 JSON 文件加载 Prompt 模板

        Returns:
            tuple: (system_prompt, user_prompt)
        """
        return PromptLoader.load_pair(self._get_prompt_key(), "light")

    @abstractmethod
    def _get_prompt_key(self) -> str:
        """
        获取 Prompt 加载的 key

        Returns:
            str: Prompt key，如 "paper" 或 "news"
        """
        ...

    @abstractmethod
    def _build_user_content(self, item: TInput) -> str:
        """
        构建用户消息内容

        Args:
            item: 输入数据项

        Returns:
            str: 用户消息内容
        """
        ...

    @abstractmethod
    def _create_output(self, item: TInput) -> TOutput:
        """
        创建输出对象

        Args:
            item: 输入数据项

        Returns:
            输出对象（初始状态为 pending）
        """
        ...

    @abstractmethod
    def _get_analysis_schema(self) -> type[TAnalysis]:
        """
        获取分析结果的 Pydantic 类

        Returns:
            Pydantic 模型类
        """
        ...

    @abstractmethod
    def _set_analysis_result(
        self,
        output: TOutput,
        analysis: TAnalysis,
    ) -> None:
        """
        设置分析结果到输出对象

        Args:
            output: 输出对象
            analysis: 分析结果
        """
        ...

    @abstractmethod
    def _get_item_id(self, item: TInput) -> str:
        """
        获取输入项的 ID（用于日志）

        Args:
            item: 输入数据项

        Returns:
            str: 项目 ID
        """
        ...

    @abstractmethod
    def _get_progress_desc(self) -> str:
        """获取进度条描述"""
        ...

    @abstractmethod
    def _get_progress_unit(self) -> str:
        """获取进度条单位"""
        ...

    def _get_language_display(self) -> str:
        """获取语言显示名称"""
        language_map = {
            "zh": "中文",
            "en": "English",
        }
        return language_map.get(self._language, self._language)

    def _build_prompt(self, item: TInput) -> list[BaseMessage]:
        """
        构建 LLM 调用的消息列表

        Args:
            item: 输入数据项

        Returns:
            LangChain 消息列表
        """
        system_content = self._system_prompt.format(
            language=self._get_language_display()
        )
        user_content = self._build_user_content(item)

        return [
            SystemMessage(content=system_content),
            HumanMessage(content=user_content),
        ]

    async def analyze_one(self, item: TInput) -> TOutput:
        """
        异步分析单个项目

        使用 Semaphore 控制并发，调用 LLM 结构化输出接口。
        失败时标记状态而非抛出异常。

        Args:
            item: 输入数据项

        Returns:
            包含分析结果的输出对象（成功或失败状态）
        """
        # 创建输出对象
        output = self._create_output(item)
        item_id = self._get_item_id(item)

        try:
            async with self._semaphore:
                start_time = time.perf_counter()
                analysis = await self._llm_client.chat_structured(
                    messages=self._build_prompt(item),
                    schema=self._get_analysis_schema(),
                )
                elapsed = time.perf_counter() - start_time
                logger.info(f"[LLM] {item_id} 耗时: {elapsed:.2f}s")

            self._set_analysis_result(output, analysis)
            output.analysis_status = "success"
            output.analyzed_at = datetime.now(timezone.utc)

        except LLMParseError as e:
            output.analysis_status = "failed"
            output.analysis_error = f"JSON 解析失败: {e}"
            logger.warning(f"{self._get_progress_desc()} {item_id} 分析失败: {e}")

        except LLMRateLimitError as e:
            output.analysis_status = "failed"
            output.analysis_error = f"API 限流: {e}"
            logger.warning(f"{self._get_progress_desc()} {item_id} 分析失败 (限流): {e}")

        except Exception as e:
            output.analysis_status = "failed"
            output.analysis_error = str(e)
            logger.error(f"{self._get_progress_desc()} {item_id} 分析异常: {e}")

        return output

    async def analyze_batch(
        self,
        items: list[TInput],
        show_progress: bool = True,
    ) -> list[TOutput]:
        """
        异步批量分析

        使用 asyncio.gather() 并发执行，支持 tqdm 进度显示。

        Args:
            items: 输入数据列表
            show_progress: 是否显示进度条，默认 True

        Returns:
            分析后的输出列表（包含成功和失败的）
        """
        if not items:
            return []

        # 创建分析任务
        tasks = [self.analyze_one(item) for item in items]

        # 执行并发分析
        if show_progress:
            results = await tqdm_asyncio.gather(
                *tasks,
                desc=self._get_progress_desc(),
                unit=self._get_progress_unit(),
            )
        else:
            results = await asyncio.gather(*tasks)

        return list(results)

    @staticmethod
    def get_analysis_stats(items: list[TOutput]) -> dict:
        """
        获取分析统计信息

        Args:
            items: 分析后的输出列表

        Returns:
            统计字典，包含 total, success, failed, success_rate
        """
        total = len(items)
        success = len([i for i in items if i.analysis_status == "success"])
        failed = len([i for i in items if i.analysis_status == "failed"])

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": success / total if total > 0 else 1.0,
        }

