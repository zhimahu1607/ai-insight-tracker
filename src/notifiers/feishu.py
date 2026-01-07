"""
飞书通知器

使用 aiohttp 异步发送飞书消息卡片。
"""

import asyncio
import logging
import os
from typing import Any, Optional
from urllib.parse import quote, urlencode

import aiohttp

from src.config import get_settings
from src.models import DailyReport, AnalyzedPaper, AnalyzedNews
from .base import BaseNotifier


logger = logging.getLogger(__name__)


class FeishuNotifier(BaseNotifier):
    """
    飞书异步通知器

    支持发送每日报告卡片和深度分析结果卡片。

    Usage:
        async with FeishuNotifier() as notifier:
            success = await notifier.send_daily_report(report)

        # 或者手动管理
        notifier = FeishuNotifier()
        await notifier.send_daily_report(report)
        await notifier.close()
    """

    # GitHub Issue 预填链接模板
    ISSUE_TEMPLATE_TITLE = "[Analysis] {paper_id}: {paper_title}"
    ISSUE_TEMPLATE_BODY = """## 请求深度分析

**论文 ID**: {paper_id}
**论文标题**: {paper_title}
**arXiv 链接**: https://arxiv.org/abs/{paper_id}

---

### 分析需求
<!-- 请选择您希望深度分析的重点方向 -->

- [ ] 技术方法详解
- [ ] 实验设计分析
- [ ] 与相关工作对比
- [ ] 潜在应用场景
- [ ] 其他：

### 补充说明
<!-- 可选：添加任何额外说明 -->

"""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
        site_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        max_papers: Optional[int] = None,
        max_news: Optional[int] = None,
    ):
        """
        初始化飞书通知器

        Args:
            webhook_url: 飞书 Webhook URL，默认从配置获取
            repo_owner: GitHub 仓库所有者，默认从环境变量获取
            repo_name: GitHub 仓库名称，默认从环境变量获取
            site_url: 网站 URL，用于"查看完整网站"按钮
            timeout: 请求超时（秒），默认从配置获取
            max_retries: 最大重试次数，默认从配置获取
            max_papers: 卡片中显示的论文数量，默认从配置获取
            max_news: 卡片中显示的热点数量，默认从配置获取
        """
        settings = get_settings()

        self._webhook_url = webhook_url or settings.notification.feishu_webhook_url
        self._timeout = timeout or settings.notification.timeout
        self._max_retries = max_retries or settings.notification.max_retries
        self._max_papers = max_papers or settings.notification.max_papers
        self._max_news = max_news or settings.notification.max_news

        # GitHub 仓库信息（用于生成 Issue 链接）
        # GITHUB_REPOSITORY 格式: owner/repo
        github_repo = os.environ.get("GITHUB_REPOSITORY", "")
        if "/" in github_repo:
            default_owner, default_name = github_repo.split("/", 1)
        else:
            default_owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
            default_name = github_repo

        self._repo_owner = repo_owner or default_owner
        self._repo_name = repo_name or default_name

        # 网站 URL（优先级：参数 > 配置文件 > 环境变量 > GitHub Pages 默认）
        self._site_url = (
            site_url 
            or settings.notification.site_url
            or os.environ.get("SITE_URL")
            or (f"https://{self._repo_owner}.github.io/{self._repo_name}" if self._repo_owner else "")
        )

        # aiohttp session（懒加载）
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def is_configured(self) -> bool:
        """检查是否已配置 Webhook URL"""
        return bool(self._webhook_url)

    async def _get_session(self) -> aiohttp.ClientSession:
        """懒加载获取或创建 aiohttp ClientSession"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            )
        return self._session

    async def close(self) -> None:
        """关闭 session，释放连接"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def send_daily_report(self, report: DailyReport) -> bool:
        """
        发送每日报告卡片

        Args:
            report: DailyReport 实例

        Returns:
            发送是否成功
        """
        if not self.is_configured:
            logger.warning("飞书 Webhook URL 未配置，跳过每日报告通知")
            return False

        card = self._build_daily_card(report)
        return await self._send_card(card)

    async def send_deep_analysis(
        self,
        paper_id: str,
        paper_title: str,
        summary: str,
        issue_url: str,
    ) -> bool:
        """
        发送深度分析结果卡片

        Args:
            paper_id: 论文 ID
            paper_title: 论文标题
            summary: 分析摘要（会自动截取前 500 字）
            issue_url: GitHub Issue 链接

        Returns:
            发送是否成功
        """
        if not self.is_configured:
            logger.warning("飞书 Webhook URL 未配置，跳过深度分析通知")
            return False

        card = self._build_analysis_card(paper_id, paper_title, summary, issue_url)
        return await self._send_card(card)

    async def _send_card(self, card: dict[str, Any]) -> bool:
        """
        发送卡片到 Webhook

        包含指数退避重试逻辑。

        Args:
            card: 卡片 JSON 数据

        Returns:
            发送是否成功
        """
        session = await self._get_session()

        for attempt in range(self._max_retries + 1):
            try:
                async with session.post(
                    self._webhook_url,
                    json={"msg_type": "interactive", "card": card},
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("code") == 0:
                            logger.info("飞书消息发送成功")
                            return True
                        else:
                            logger.warning(
                                f"飞书 API 返回错误: {result.get('msg', 'unknown')}"
                            )
                    else:
                        logger.warning(f"飞书 API 返回状态码: {response.status}")

            except aiohttp.ClientError as e:
                logger.warning(f"飞书消息发送失败 (尝试 {attempt + 1}): {e}")

            except asyncio.TimeoutError:
                logger.warning(f"飞书消息发送超时 (尝试 {attempt + 1})")

            # 指数退避重试
            if attempt < self._max_retries:
                delay = 2 ** attempt  # 1s, 2s, 4s
                await asyncio.sleep(delay)

        logger.error(f"飞书消息发送失败，已重试 {self._max_retries} 次")
        return False

    def _build_issue_url(self, paper_id: str, paper_title: str) -> str:
        """
        生成预填的 GitHub Issue 创建链接

        Args:
            paper_id: 论文 ID
            paper_title: 论文标题

        Returns:
            预填的 Issue 创建 URL
        """
        if not self._repo_owner or not self._repo_name:
            return ""

        # 截断标题（避免 URL 过长）
        truncated_title = paper_title[:50] + "..." if len(paper_title) > 50 else paper_title

        title = self.ISSUE_TEMPLATE_TITLE.format(
            paper_id=paper_id,
            paper_title=truncated_title,
        )

        body = self.ISSUE_TEMPLATE_BODY.format(
            paper_id=paper_id,
            paper_title=paper_title,
        )

        params = urlencode({
            "title": title,
            "body": body,
            "labels": "agent-task",
        }, quote_via=quote)

        return f"https://github.com/{self._repo_owner}/{self._repo_name}/issues/new?{params}"

    def _build_daily_card(self, report: DailyReport) -> dict[str, Any]:
        """
        构建每日报告卡片

        Args:
            report: DailyReport 实例

        Returns:
            飞书卡片 JSON
        """
        elements: list[dict[str, Any]] = []

        # === 总结区域 ===
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": report.summary,
            },
        })

        elements.append({"tag": "hr"})

        # === 精选论文 ===
        highlight_papers = report.get_highlight_papers(self._max_papers)
        if highlight_papers:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📚 **精选论文** ({len(highlight_papers)})",
                },
            })

            for paper in highlight_papers:
                elements.extend(self._build_paper_elements(paper))

            elements.append({"tag": "hr"})

        # === 热点资讯 ===
        highlight_news = report.get_highlight_news(self._max_news)
        if highlight_news:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"🔥 **热点资讯** ({len(highlight_news)})",
                },
            })

            for item in highlight_news:
                elements.append(self._build_news_element(item))

            elements.append({"tag": "hr"})

        # === 底部按钮 ===
        bottom_actions: list[dict[str, Any]] = []
        
        # 查看今日全部论文按钮
        if self._site_url:
            papers_url = f"{self._site_url.rstrip('/')}/#/papers?date={report.date}"
            bottom_actions.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": f"📚 查看今日全部论文 ({report.paper_count}篇)",
                },
                "type": "primary",
                "url": papers_url,
            })
            
            # 查看今日全部热点按钮
            news_url = f"{self._site_url.rstrip('/')}/#/news?date={report.date}"
            bottom_actions.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": f"🔥 查看今日全部热点 ({report.news_count}条)",
                },
                "type": "default",
                "url": news_url,
            })
        
        if bottom_actions:
            elements.append({
                "tag": "action",
                "actions": bottom_actions,
            })

        return {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 AI Insight Tracker 日报 - {report.date}",
                },
                "template": "blue",
            },
            "elements": elements,
        }

    def _build_paper_elements(self, paper: AnalyzedPaper) -> list[dict[str, Any]]:
        """
        构建单篇论文的卡片元素

        Args:
            paper: AnalyzedPaper 实例

        Returns:
            卡片元素列表
        """
        elements: list[dict[str, Any]] = []

        # 论文标题和概述
        overview = ""
        if paper.light_analysis:
            overview = paper.light_analysis.overview

        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**[{paper.id}] {paper.title}**\n{overview}",
            },
        })

        # 操作按钮
        actions: list[dict[str, Any]] = [
            {
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "📄 查看详情",
                },
                "type": "default",
                "url": str(paper.abs_url),
            },
        ]

        # 深度分析按钮（需要配置 GitHub 仓库信息）
        issue_url = self._build_issue_url(paper.id, paper.title)
        if issue_url:
            actions.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "🔬 请求深度分析",
                },
                "type": "default",
                "url": issue_url,
            })

        elements.append({
            "tag": "action",
            "actions": actions,
        })

        return elements

    def _build_news_element(self, item: AnalyzedNews) -> dict[str, Any]:
        """
        构建单条热点的卡片元素

        Args:
            item: AnalyzedNews 实例

        Returns:
            卡片元素
        """
        summary = ""
        if item.light_analysis:
            summary = f" - {item.light_analysis.summary[:50]}..."

        return {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"• [{item.title}]({item.url}){summary} - {item.source_name}",
            },
        }

    def _build_analysis_card(
        self,
        paper_id: str,
        paper_title: str,
        summary: str,
        issue_url: str,
    ) -> dict[str, Any]:
        """
        构建深度分析结果卡片

        Args:
            paper_id: 论文 ID
            paper_title: 论文标题
            summary: 分析摘要
            issue_url: GitHub Issue 链接

        Returns:
            飞书卡片 JSON
        """
        # 截取摘要前 500 字
        truncated_summary = summary[:500] + "..." if len(summary) > 500 else summary

        elements: list[dict[str, Any]] = [
            # 论文标题
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**论文标题**: {paper_title}",
                },
            },
            {"tag": "hr"},
            # 分析摘要
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**分析摘要**:\n\n{truncated_summary}",
                },
            },
            {"tag": "hr"},
            # 查看完整分析按钮
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "📖 查看完整分析",
                        },
                        "type": "primary",
                        "url": issue_url,
                    },
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "📄 arXiv 原文",
                        },
                        "type": "default",
                        "url": f"https://arxiv.org/abs/{paper_id}",
                    },
                ],
            },
        ]

        return {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🔬 深度分析完成 - {paper_id}",
                },
                "template": "green",
            },
            "elements": elements,
        }


def get_notifier() -> BaseNotifier:
    """
    获取通知器实例

    根据配置返回合适的通知器:
    - 已配置飞书 Webhook: 返回 FeishuNotifier
    - 未配置: 返回 DummyNotifier

    Returns:
        BaseNotifier 实例
    """
    from .base import DummyNotifier

    settings = get_settings()

    if settings.notification.feishu_webhook_url:
        return FeishuNotifier()
    else:
        return DummyNotifier(reason="飞书 Webhook URL 未配置")

