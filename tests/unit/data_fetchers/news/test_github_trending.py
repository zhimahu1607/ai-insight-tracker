"""Tests for GitHub Trending parsing and README preparation."""

from src.data_fetchers.news.github_readme import clean_readme_text
from src.data_fetchers.news.github_trending import (
    GitHubTrendingFetcher,
    parse_star_count,
    parse_trending_repositories,
)
from src.prompts.news import news_light_system_prompt


TRENDING_HTML = """
<html>
  <body>
    <article class="Box-row">
      <h2><a href="/owner/large-repo"> owner / large-repo </a></h2>
      <p>A useful AI framework.</p>
      <span itemprop="programmingLanguage">Python</span>
      <a href="/owner/large-repo/stargazers">1,234</a>
      <span class="d-inline-block float-sm-right">234 stars this week</span>
    </article>
    <article class="Box-row">
      <h2><a href="/owner/exact-threshold"> owner / exact-threshold </a></h2>
      <p>Should be filtered because stars must be greater than threshold.</p>
      <a href="/owner/exact-threshold/stargazers">1,000</a>
      <span class="d-inline-block float-sm-right">50 stars this week</span>
    </article>
    <article class="Box-row">
      <h2><a href="/owner/large-repo"> owner / large-repo </a></h2>
      <p>Duplicate repo.</p>
      <a href="/owner/large-repo/stargazers">2,000</a>
      <span class="d-inline-block float-sm-right">500 stars this week</span>
    </article>
  </body>
</html>
"""


def test_parse_star_count():
    assert parse_star_count("1,234") == 1234
    assert parse_star_count("2.5k stars this week") == 2500
    assert parse_star_count("1.2m") == 1_200_000
    assert parse_star_count("no stars") == 0


def test_parse_trending_repositories_filters_and_dedups():
    repos = parse_trending_repositories(TRENDING_HTML, limit=25, min_stars=1000)

    assert len(repos) == 1
    repo = repos[0]
    assert repo.repo_id == "owner/large-repo"
    assert repo.full_name == "owner/large-repo"
    assert repo.url == "https://github.com/owner/large-repo"
    assert repo.description == "A useful AI framework."
    assert repo.language == "Python"
    assert repo.stars == 1234
    assert repo.weekly_stars == 234


def test_clean_readme_text_removes_code_and_badges():
    raw = """
# Example

![build](https://img.shields.io/badge/build-passing-green)

Example helps developers build AI apps with a small runtime.

```python
print("implementation details")
```

See [docs](https://example.com/docs) for usage.
"""

    cleaned = clean_readme_text(raw, max_chars=200)

    assert "Example" in cleaned
    assert "AI apps" in cleaned
    assert "docs" in cleaned
    assert "implementation details" not in cleaned
    assert "shields.io" not in cleaned


def test_clean_readme_text_truncates():
    cleaned = clean_readme_text("a" * 100, max_chars=20)

    assert cleaned == "a" * 20


def test_build_trending_url_uses_weekly_language_path():
    fetcher = GitHubTrendingFetcher()

    assert fetcher._build_url("") == "https://github.com/trending"
    assert fetcher._build_url("python") == "https://github.com/trending/python"


def test_news_prompt_constrains_github_trending_to_readme():
    assert "GitHub Trending" in news_light_system_prompt
    assert "README" in news_light_system_prompt
    assert "不要假装读过仓库源码" in news_light_system_prompt
