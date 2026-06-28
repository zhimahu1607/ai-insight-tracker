"""GitHub Trending weekly repository fetcher."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import aiohttp
from bs4 import BeautifulSoup

from src.models import FetchType, NewsItem

from .github_readme import GitHubReadmeFetcher
from .github_trending_state import (
    DOUBLE_IN_7_DAYS,
    TEN_X_STARS,
    GitHubTrendingState,
)
from .rss_parser import generate_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GitHubTrendingRepo:
    repo_id: str
    owner: str
    name: str
    full_name: str
    url: str
    description: str
    language: Optional[str]
    stars: int
    weekly_stars: int
    readme_text: Optional[str] = None


class GitHubTrendingFetcher:
    """Fetch GitHub Trending repositories as NewsItem objects."""

    BASE_URL = "https://github.com/trending"

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        readme_max_chars: int = 8000,
        state_path: str | Path = "data/github_trending_repos.json",
    ) -> None:
        self._timeout = timeout
        self._readme_fetcher = GitHubReadmeFetcher(
            timeout=timeout,
            max_chars=readme_max_chars,
        )
        self._state = GitHubTrendingState(state_path)

    async def fetch(
        self,
        *,
        since: str = "weekly",
        language: str = "",
        limit: int = 25,
        min_stars: int = 1000,
        weight: float = 0.9,
    ) -> list[NewsItem]:
        """Fetch weekly Trending repos and return new repo/alert items."""
        observed_at = datetime.now(timezone.utc)
        html = await self._fetch_trending_html(since=since, language=language)
        if not html:
            return []

        repos = parse_trending_repositories(html, limit=limit, min_stars=min_stars)
        if not repos:
            logger.info("GitHub Trending returned no repos above %s stars", min_stars)
            return []

        items: list[NewsItem] = []
        for repo in repos:
            if self._state.has_repo(repo.repo_id):
                decision = self._state.process_observation(
                    repo_id=repo.repo_id,
                    full_name=repo.full_name,
                    url=repo.url,
                    stars=repo.stars,
                    observed_at=observed_at,
                )
                for alert in decision.alerts:
                    repo_with_readme = await self._with_readme_for_alert(repo)
                    items.append(
                        _repo_to_alert_item(
                            repo_with_readme,
                            alert=alert,
                            observed_at=observed_at,
                            weight=weight,
                        )
                    )
                continue

            repo_with_readme = await self._with_readme(repo)
            decision = self._state.process_observation(
                repo_id=repo.repo_id,
                full_name=repo.full_name,
                url=repo.url,
                stars=repo.stars,
                observed_at=observed_at,
            )
            if repo_with_readme.readme_text is None:
                logger.info(
                    "Recorded GitHub Trending repo but skipped item without README: %s",
                    repo.full_name,
                )
                continue

            if decision.is_new:
                items.append(
                    _repo_to_news_item(
                        repo_with_readme,
                        observed_at=observed_at,
                        weight=weight,
                    )
                )

        self._state.save()
        logger.info("GitHub Trending fetched %s new/alert items", len(items))
        return items

    async def _fetch_trending_html(self, *, since: str, language: str) -> Optional[str]:
        url = self._build_url(language)
        params = {"since": since}
        headers = {"User-Agent": "ai-insight-tracker"}

        try:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url, params=params) as response:
                    if response.status >= 400:
                        logger.warning(
                            "GitHub Trending fetch failed: HTTP %s",
                            response.status,
                        )
                        return None
                    return await response.text()
        except (aiohttp.ClientError, TimeoutError) as e:
            logger.warning("GitHub Trending fetch failed: %s", e)
            return None

    def _build_url(self, language: str) -> str:
        language = language.strip().strip("/")
        if not language:
            return self.BASE_URL
        return f"{self.BASE_URL}/{quote(language)}"

    async def _with_readme(self, repo: GitHubTrendingRepo) -> GitHubTrendingRepo:
        readme_text = await self._readme_fetcher.fetch_readme(repo.owner, repo.name)
        return GitHubTrendingRepo(**{**repo.__dict__, "readme_text": readme_text})

    async def _with_readme_for_alert(
        self,
        repo: GitHubTrendingRepo,
    ) -> GitHubTrendingRepo:
        readme_text = await self._readme_fetcher.fetch_readme(repo.owner, repo.name)
        return GitHubTrendingRepo(**{**repo.__dict__, "readme_text": readme_text})


def parse_trending_repositories(
    html: str,
    *,
    limit: int = 25,
    min_stars: int = 1000,
) -> list[GitHubTrendingRepo]:
    """Parse GitHub Trending HTML into repositories."""
    soup = BeautifulSoup(html, "html.parser")
    repos: list[GitHubTrendingRepo] = []
    seen: set[str] = set()

    for article in soup.select("article.Box-row"):
        link = article.select_one("h2 a")
        if link is None:
            continue

        href = (link.get("href") or "").strip()
        parts = [part for part in href.strip("/").split("/") if part]
        if len(parts) < 2:
            continue

        owner, name = parts[0], parts[1]
        full_name = f"{owner}/{name}"
        repo_id = full_name.lower()
        if repo_id in seen:
            continue
        seen.add(repo_id)

        stars = _extract_stars(article)
        if stars <= min_stars:
            continue

        language = _extract_text(article.select_one("[itemprop='programmingLanguage']"))
        description = _extract_text(article.select_one("p"))
        weekly_stars = _extract_weekly_stars(article)

        repos.append(
            GitHubTrendingRepo(
                repo_id=repo_id,
                owner=owner,
                name=name,
                full_name=full_name,
                url=f"https://github.com/{owner}/{name}",
                description=description,
                language=language or None,
                stars=stars,
                weekly_stars=weekly_stars,
            )
        )

        if limit > 0 and len(repos) >= limit:
            break

    return repos


def _repo_to_news_item(
    repo: GitHubTrendingRepo,
    *,
    observed_at: datetime,
    weight: float,
) -> NewsItem:
    metadata = _format_repo_metadata(repo)
    content = f"{metadata}\n\nREADME:\n{repo.readme_text or ''}".strip()
    return NewsItem(
        id=generate_id(repo.url),
        title=f"{repo.full_name} - GitHub Trending",
        url=repo.url,
        source_name="GitHub Trending",
        source_category="opensource",
        language="en",
        published=observed_at,
        summary=metadata,
        content=content,
        weight=weight,
        fetch_type=FetchType.CRAWLER,
        company="github",
    )


def _repo_to_alert_item(
    repo: GitHubTrendingRepo,
    *,
    alert: str,
    observed_at: datetime,
    weight: float,
) -> NewsItem:
    if alert == DOUBLE_IN_7_DAYS:
        alert_title = "stars doubled within 7 days"
        alert_text = "Star growth alert: stars doubled within 7 days."
    elif alert == TEN_X_STARS:
        alert_title = "stars reached 10x baseline"
        alert_text = "Star growth alert: stars reached 10x the first tracked count."
    else:
        alert_title = "star growth alert"
        alert_text = "Star growth alert."

    metadata = f"{alert_text}\n{_format_repo_metadata(repo)}"
    if repo.readme_text:
        content = f"{metadata}\n\nREADME:\n{repo.readme_text}"
    else:
        content = metadata

    return NewsItem(
        id=generate_id(f"{repo.url}#stars-alert:{alert}"),
        title=f"GitHub Trending Alert: {repo.full_name} {alert_title}",
        url=repo.url,
        source_name="GitHub Trending",
        source_category="opensource",
        language="en",
        published=observed_at,
        summary=metadata,
        content=content,
        weight=weight,
        fetch_type=FetchType.CRAWLER,
        company="github",
    )


def _format_repo_metadata(repo: GitHubTrendingRepo) -> str:
    return "\n".join(
        [
            f"Repository: {repo.full_name}",
            f"URL: {repo.url}",
            f"Description: {repo.description or 'No description'}",
            f"Language: {repo.language or 'Unknown'}",
            f"Stars: {repo.stars}",
            f"Weekly stars: {repo.weekly_stars}",
        ]
    )


def _extract_stars(article: object) -> int:
    link = article.select_one('a[href$="/stargazers"]')  # type: ignore[attr-defined]
    return parse_star_count(_extract_text(link))


def _extract_weekly_stars(article: object) -> int:
    candidates = article.select("span")  # type: ignore[attr-defined]
    for candidate in candidates:
        text = _extract_text(candidate)
        if "stars this" in text:
            return parse_star_count(text)
    return 0


def _extract_text(node: object) -> str:
    if node is None:
        return ""
    text = node.get_text(" ", strip=True)  # type: ignore[attr-defined]
    return re.sub(r"\s+", " ", text).strip()


def parse_star_count(text: str) -> int:
    """Parse GitHub star count strings such as '1,234' or '2.3k stars this week'."""
    match = re.search(r"([\d,.]+)\s*([kKmM]?)", text.replace(",", ""))
    if not match:
        return 0

    value = float(match.group(1))
    suffix = match.group(2).lower()
    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000
    return int(value)
