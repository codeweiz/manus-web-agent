from typing import Generic, TypeVar, Optional

from pydantic import BaseModel, Field

T = TypeVar("T")


class ToolResult(BaseModel, Generic[T], ):
    """工具执行结果"""

    success: bool = Field(..., description="是否成功")

    message: Optional[str] = Field(default=None, description="消息")

    data: Optional[T] = Field(default=None, description="数据")
