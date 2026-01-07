"""
LLM 客户端异常定义
"""


class LLMError(Exception):
    """LLM 调用基础异常"""

    pass


class LLMRateLimitError(LLMError):
    """速率限制异常，应等待后重试"""

    def __init__(self, message: str = "API 请求频率超限", retry_after: float = 0):
        super().__init__(message)
        self.retry_after = retry_after


class LLMTimeoutError(LLMError):
    """请求超时异常"""

    pass


class LLMAuthError(LLMError):
    """认证失败异常 (API Key 无效)"""

    pass


class LLMParseError(LLMError):
    """结构化输出 JSON 解析失败"""

    def __init__(self, message: str, raw_response: str = ""):
        super().__init__(message)
        self.raw_response = raw_response

