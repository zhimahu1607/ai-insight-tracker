"""
Prompt templates for AI Insight Tracker.

This module provides centralized prompt management for all agents and generators.
"""

from .paper import (
    # Light analyzer prompts
    paper_light_system_prompt,
    paper_light_user_prompt,
    # Deep analyzer prompts
    paper_supervisor_prompt,
    paper_researcher_prompt,
    paper_writer_prompt,
    paper_reviewer_prompt,
)

from .news import (
    news_light_system_prompt,
    news_light_user_prompt,
)

from .report import (
    REPORT_SYSTEM_PROMPT,
    CATEGORY_SUMMARY_USER_PROMPT,
    NEWS_SUMMARY_USER_PROMPT,
    DAILY_SUMMARY_USER_PROMPT,
)

__all__ = [
    # Paper prompts
    "paper_light_system_prompt",
    "paper_light_user_prompt",
    "paper_supervisor_prompt",
    "paper_researcher_prompt",
    "paper_writer_prompt",
    "paper_reviewer_prompt",
    # News prompts
    "news_light_system_prompt",
    "news_light_user_prompt",
    # Report prompts
    "REPORT_SYSTEM_PROMPT",
    "CATEGORY_SUMMARY_USER_PROMPT",
    "NEWS_SUMMARY_USER_PROMPT",
    "DAILY_SUMMARY_USER_PROMPT",
]

