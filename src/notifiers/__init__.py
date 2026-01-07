"""
通知模块

提供异步通知能力，支持飞书等平台。
"""

from .base import BaseNotifier, DummyNotifier
from .feishu import FeishuNotifier, get_notifier

__all__ = [
    "BaseNotifier",
    "DummyNotifier",
    "FeishuNotifier",
    "get_notifier",
]
