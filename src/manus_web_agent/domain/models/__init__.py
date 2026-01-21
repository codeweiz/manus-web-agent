from typing import Optional, List

from pydantic import BaseModel, Field


class ProcessInfo(BaseModel):
    """进程信息"""

    name: str = Field(..., description="进程名")

    group: str = Field(..., description="进程组")

    description: str = Field(..., description="描述")

    start: int = Field(..., description="启动时间")

    stop: int = Field(..., description="停止时间")

    now: int = Field(..., description="当前时间")

    state: int = Field(..., description="状态")

    state_name: str = Field(..., description="状态名")

    spawn_err: str = Field(..., description="spawn 错误信息")

    exit_status: int = Field(..., description="退出状态")

    logfile: str = Field(..., description="日志文件")

    stdout_logfile: str = Field(..., description="标准输出日志文件")

    stderr_logfile: str = Field(..., description="标准错误日志文件")

    pid: int = Field(..., description="进程 ID")


class SupervisorActionResult(BaseModel):
    """Supervisor 操作结果"""

    status: str = Field(..., description="状态")

    result: Optional[List[str]] = Field(default=None, description="结果")

    stop_result: Optional[List[str]] = Field(default=None, description="停止结果")

    start_result: Optional[List[str]] = Field(default=None, description="启动结果")

    shutdown_result: Optional[List[str]] = Field(default=None, description="关闭结果")


class SupervisorTimeout(BaseModel):
    """Supervisor 超时结果"""

    status: str = Field(..., description="状态")

    activate: bool = Field(default=False, description="是否激活")

    shutdown_time: Optional[str] = Field(default=None, description="关闭时间")

    timeout_minutes: Optional[float] = Field(default=None, description="超时分钟数")

    remain_seconds: Optional[float] = Field(default=None, description="剩余秒数")
