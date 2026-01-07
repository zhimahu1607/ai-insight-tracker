"""
arXiv PDF 异步下载器

支持异步下载、临时存储、自动清理。
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class PDFDownloader:
    """
    arXiv PDF 异步下载器

    Features:
        - 异步下载，支持超时和重试
        - 使用临时文件，解析后自动清理
        - 遵守 arXiv 限流规则
    """

    def __init__(
        self,
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        """
        初始化下载器

        Args:
            timeout: 下载超时时间（秒）
            max_retries: 最大重试次数
        """
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._max_retries = max_retries

    async def download(
        self,
        paper_id: str,
        pdf_url: Optional[str] = None,
    ) -> Path:
        """
        下载 PDF 文件到临时目录

        Args:
            paper_id: arXiv 论文 ID
            pdf_url: PDF URL（可选，默认根据 ID 构建）

        Returns:
            临时 PDF 文件路径

        Raises:
            RuntimeError: 下载失败
        """
        # 构建 URL
        if pdf_url is None:
            pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"

        logger.info(f"下载 PDF: {pdf_url}")

        # 创建临时文件
        safe_id = paper_id.replace("/", "_")
        temp_dir = Path(tempfile.gettempdir()) / "ai-insight-tracker"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"{safe_id}.pdf"

        # 带重试的下载
        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self._timeout) as session:
                    headers = {"User-Agent": "AI-Insight-Tracker/1.0"}
                    async with session.get(pdf_url, headers=headers) as response:
                        if response.status == 200:
                            content = await response.read()
                            temp_path.write_bytes(content)
                            logger.info(
                                f"PDF 下载完成: {temp_path} ({len(content)} bytes)"
                            )
                            return temp_path
                        elif response.status == 429:
                            # 限流，等待后重试
                            wait_time = 30
                            logger.warning(f"arXiv 限流，等待 {wait_time}s 后重试")
                            await asyncio.sleep(wait_time)
                        else:
                            raise RuntimeError(f"HTTP {response.status}")

            except asyncio.TimeoutError as e:
                last_error = e
                wait_time = 2**attempt
                logger.warning(
                    f"下载超时，等待 {wait_time}s 后重试 ({attempt + 1}/{self._max_retries})"
                )
                await asyncio.sleep(wait_time)

            except aiohttp.ClientError as e:
                last_error = e
                wait_time = 2**attempt
                logger.warning(
                    f"下载失败: {e}，等待 {wait_time}s 后重试 ({attempt + 1}/{self._max_retries})"
                )
                await asyncio.sleep(wait_time)

            except Exception as e:
                last_error = e
                logger.error(f"下载异常: {e}")
                break

        raise RuntimeError(f"PDF 下载失败: {last_error}")

    @staticmethod
    def cleanup(pdf_path: Path) -> None:
        """
        清理临时 PDF 文件

        Args:
            pdf_path: PDF 文件路径
        """
        try:
            if pdf_path.exists():
                pdf_path.unlink()
                logger.debug(f"已清理临时文件: {pdf_path}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

