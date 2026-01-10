"""
共享状态码定义

用于脚本退出码、采集/去重流程状态传递等场景，避免重复定义导致语义漂移。
"""

from enum import IntEnum


class DedupStatus(IntEnum):
    """去重/采集返回状态码（向后兼容历史 int 常量）"""

    HAS_NEW_CONTENT = 0  # 有新内容，继续处理
    NO_NEW_CONTENT = 1  # 无新内容
    PROCESS_ERROR = 2  # 处理错误


