from typing import Optional, List

from pydantic import BaseModel, Field


class ConsoleRecord(BaseModel):
    """控制台记录"""

    ps1: str = Field(..., description="提示符")

    command: str = Field(..., description="命令")

    output: str = Field(default="", description="输出")


class ShellTask(BaseModel):
    """Shell 任务"""

    id: str = Field(..., description="任务 ID")

    command: str = Field(..., description="命令")

    status: str = Field(..., description="状态")

    created_at: str = Field(..., description="创建时间")

    output: Optional[str] = Field(default=None, description="输出")


class ShellExecResult(BaseModel):
    """Shell 执行结果"""

    session_id: str = Field(..., description="会话 ID")

    command: str = Field(..., description="命令")

    status: str = Field(..., description="状态")

    return_code: Optional[int] = Field(default=None, description="返回码")

    output: Optional[str] = Field(default=None, description="输出")


class ShellViewResult(BaseModel):
    """Shell 查看结果"""

    session_id: str = Field(..., description="会话 ID")

    output: str = Field(..., description="输出")

    console: Optional[List[ConsoleRecord]] = Field(default=None, description="控制台记录")


class ShellWaitResult(BaseModel):
    """Shell 等待结果"""

    return_code: Optional[int] = Field(default=None, description="返回码")


class ShellWriteResult(BaseModel):
    """Shell 写入结果"""

    status: str = Field(..., description="状态")


class ShellKillResult(BaseModel):
    """Shell 杀死结果"""

    status: str = Field(..., description="状态")

    return_code: Optional[int] = Field(default=None, description="返回码")
