from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """基础 API 响应 Schema"""

    code: int = 0
    msg: str = "success"
    data: Optional[T] = None

    @staticmethod
    def success(data: Optional[T] = None, msg: str = "success") -> "APIResponse[T]":
        """成功响应"""
        return APIResponse(code=0, msg=msg, data=data)

    @staticmethod
    def error(code: int, msg: str) -> "APIResponse[T]":
        """错误响应"""
        return APIResponse(code=code, msg=msg, data=None)
