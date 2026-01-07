"""
共享类型定义

提供多模块复用的类型别名和验证器，避免重复定义和循环导入。
"""

from typing import Annotated

from pydantic import AfterValidator


def validate_tags_length(v: list[str]) -> list[str]:
    """验证标签列表长度为 3-5 个"""
    if len(v) < 3:
        raise ValueError("标签列表至少需要 3 个元素")
    if len(v) > 5:
        raise ValueError("标签列表最多包含 5 个元素")
    return v


def validate_keywords_length(v: list[str]) -> list[str]:
    """验证关键词列表长度最多 5 个"""
    if len(v) > 5:
        raise ValueError("关键词列表最多包含 5 个元素")
    return v


# 带长度限制的类型别名
Tags = Annotated[list[str], AfterValidator(validate_tags_length)]
Keywords = Annotated[list[str], AfterValidator(validate_keywords_length)]

