"""应用层异常定义"""

from typing import Optional


class AppException(Exception):
    """应用层基础异常"""

    def __init__(self, message: str, code: int = 500, status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(AppException):
    """资源未找到异常"""

    def __init__(self, message: str = "资源未找到"):
        super().__init__(message, code=404, status_code=404)


class UnauthorizedError(AppException):
    """未授权异常"""

    def __init__(self, message: str = "未授权"):
        super().__init__(message, code=401, status_code=401)


class ForbiddenError(AppException):
    """禁止访问异常"""

    def __init__(self, message: str = "禁止访问"):
        super().__init__(message, code=403, status_code=403)


class ValidationError(AppException):
    """验证错误异常"""

    def __init__(self, message: str = "验证错误"):
        super().__init__(message, code=400, status_code=400)


class ConflictError(AppException):
    """资源冲突异常"""

    def __init__(self, message: str = "资源冲突"):
        super().__init__(message, code=409, status_code=409)


class RateLimitError(AppException):
    """速率限制异常"""

    def __init__(self, message: str = "请求过于频繁"):
        super().__init__(message, code=429, status_code=429)
