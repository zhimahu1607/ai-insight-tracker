"""
GitHub README fetcher.

Only README text is fetched for LLM summaries. Repositories are never cloned and
source files are never traversed.
"""

from __future__ import annotations

import base64
import logging
import re
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class GitHubReadmeFetcher:
    """Fetch and clean README text for a GitHub repository."""

    API_BASE = "https://api.github.com"

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        max_chars: int = 8000,
    ) -> None:
        self._timeout = timeout
        self._max_chars = max_chars

    async def fetch_readme(self, owner: str, repo: str) -> Optional[str]:
        """Fetch README content via GitHub API and return cleaned text."""
        url = f"{self.API_BASE}/repos/{owner}/{repo}/readme"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ai-insight-tracker",
        }

        try:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as response:
                    if response.status == 404:
                        logger.info("README not found for %s/%s", owner, repo)
                        return None
                    if response.status >= 400:
                        logger.warning(
                            "Failed to fetch README for %s/%s: HTTP %s",
                            owner,
                            repo,
                            response.status,
                        )
                        return None

                    data = await response.json()
                    raw = await self._decode_readme_payload(session, data)
        except (aiohttp.ClientError, TimeoutError, ValueError) as e:
            logger.warning("Failed to fetch README for %s/%s: %s", owner, repo, e)
            return None

        cleaned = clean_readme_text(raw, max_chars=self._max_chars)
        return cleaned or None

    async def _decode_readme_payload(
        self,
        session: aiohttp.ClientSession,
        data: dict[str, Any],
    ) -> str:
        content = data.get("content")
        encoding = data.get("encoding")
        if isinstance(content, str) and encoding == "base64":
            compact = "".join(content.split())
            return base64.b64decode(compact).decode("utf-8", errors="replace")

        download_url = data.get("download_url")
        if isinstance(download_url, str) and download_url:
            async with session.get(download_url) as response:
                if response.status >= 400:
                    raise ValueError(f"download_url returned HTTP {response.status}")
                return await response.text()

        raise ValueError("README payload has no decodable content")


def clean_readme_text(text: str, *, max_chars: int = 8000) -> str:
    """Clean Markdown README text before sending it to the LLM."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Drop fenced code blocks to avoid feeding implementation details.
    text = re.sub(r"```.*?```", "\n", text, flags=re.DOTALL)
    text = re.sub(r"~~~.*?~~~", "\n", text, flags=re.DOTALL)

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue
        if _is_badge_or_image_line(stripped):
            continue

        stripped = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", stripped)
        stripped = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", stripped)
        stripped = re.sub(r"<[^>]+>", " ", stripped)
        stripped = stripped.replace("`", "")
        stripped = re.sub(r"^[#>*\-\s]+", "", stripped)
        stripped = re.sub(r"\s+", " ", stripped).strip()
        if stripped:
            cleaned_lines.append(stripped)

    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    if max_chars > 0 and len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip()

    return cleaned


def _is_badge_or_image_line(line: str) -> bool:
    lower = line.lower()
    if lower.startswith("!["):
        return True
    badge_markers = (
        "shields.io",
        "badge",
        "github.com/actions",
        "github/workflows",
        "codecov",
    )
    return any(marker in lower for marker in badge_markers)
