import uuid
from datetime import datetime
from enum import Enum
from typing import Literal, Optional, List, Any, Union, Dict

from pydantic import BaseModel, Field

from manus_web_agent.domain.models.file import FileInfo
from manus_web_agent.domain.models.plan import Plan, Step
from manus_web_agent.domain.models.search import SearchResultItem


class PlanStatus(str, Enum):
    """计划状态枚举"""

    CREATED = "created"
    UPDATED = "updated"
    COMPLETED = "completed"


class StepStatus(str, Enum):
    """步骤状态枚举"""

    STARTED = "started"
    FAILED = "failed"
    COMPLETED = "completed"


class ToolStatus(str, Enum):
    """工具状态枚举"""

    CALLING = "calling"
    CALLED = "called"


class BrowserToolContent(BaseModel):
    """浏览器工具内容"""

    screenshot: str = Field(..., description="截图")


class SearchToolContent(BaseModel):
    """搜索工具内容"""

    results: List[SearchResultItem] = Field(..., description="搜索结果")


class ShellToolContent(BaseModel):
    """Shell 工具内容"""

    console: Any = Field(..., description="Shell 控制台输出")


class FileToolContent(BaseModel):
    """文件工具内容"""

    content: str = Field(..., description="文件内容")


class MCPToolContent(BaseModel):
    """MCP 工具内容"""

    result: Any = Field(..., description="MCP 结果")


# 工具内容
ToolContent = Union[
    BrowserToolContent,
    SearchToolContent,
    ShellToolContent,
    FileToolContent,
    MCPToolContent,
]


class BaseEvent(BaseModel):
    """基础 Agent Event"""

    type: Literal[""] = Field(default="", description="事件类型")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="事件 ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(), description="时间戳")


class ErrorEvent(BaseEvent):
    """失败 Event"""

    type: Literal["error"] = Field(default="error", description="事件类型")
    error: str = Field(..., description="错误消息")


class PlanEvent(BaseEvent):
    """计划 Event"""

    type: Literal["plan"] = Field(default="plan", description="事件类型")
    plan: Plan = Field(..., description="计划 ID")
    status: PlanStatus = Field(..., description="计划状态")
    step: Optional[Step] = Field(default=None, description="步骤")


class ToolEvent(BaseEvent):
    """工具 Event"""

    type: Literal["tool"] = Field(default="tool", description="事件类型")
    tool_call_id: str = Field(..., description="工具调用 ID")
    tool_name: str = Field(..., description="工具名")
    tool_content: Optional[ToolContent] = Field(default=None, description="工具内容")
    function_name: str = Field(..., description="工具名")
    function_args: Dict[str, Any] = Field(..., description="工具参数")
    status: ToolStatus = Field(..., description="工具状态")
    function_result: Optional[Any] = Field(default=None, description="工具结果")


class TitleEvent(BaseEvent):
    """标题 Event"""

    type: Literal["title"] = Field(default="title", description="事件类型")
    title: str = Field(..., description="标题")


class StepEvent(BaseEvent):
    """步骤 Event"""

    type: Literal["step"] = Field(default="step", description="事件类型")
    step: Step = Field(..., description="步骤")
    status: StepStatus = Field(..., description="步骤状态")


class MessageEvent(BaseEvent):
    """消息 Event"""

    type: Literal["message"] = Field(default="message", description="事件类型")
    role: Literal["user", "assistant"] = Field(default="assistant", description="角色")
    message: str = Field(..., description="消息内容")
    attachments: Optional[List[FileInfo]] = Field(default=None, description="附件")


class DoneEvent(BaseEvent):
    """完成 Event"""

    type: Literal["done"] = Field(default="done", description="事件类型")


class WaitEvent(BaseEvent):
    """等待 Event"""

    type: Literal["wait"] = Field(default="wait", description="事件类型")


# Agent Event
AgentEvent = Union[
    ErrorEvent,
    PlanEvent,
    ToolEvent,
    TitleEvent,
    StepEvent,
    MessageEvent,
    DoneEvent,
    WaitEvent,
]
