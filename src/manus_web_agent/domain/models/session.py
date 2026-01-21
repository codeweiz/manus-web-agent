import uuid
from datetime import datetime, UTC
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field

from manus_web_agent.domain.models.event import AgentEvent, PlanEvent
from manus_web_agent.domain.models.file import FileInfo
from manus_web_agent.domain.models.plan import Plan


class SessionStatus(str, Enum):
    """会话状态"""

    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"


class Session(BaseModel):
    """会话"""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16], description="会话 ID")

    user_id: str = Field(..., description="用户 ID")

    sandbox_id: Optional[str] = Field(default=None, description="沙箱 ID")

    agent_id: str = Field(..., description="代理 ID")

    task_id: Optional[str] = Field(default=None, description="任务 ID")

    title: Optional[str] = Field(default=None, description="标题")

    unread_message_count: int = Field(default=0, description="未读消息数")

    latest_message: Optional[str] = Field(default=None, description="最新消息")

    latest_message_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(UTC), description="最新消息时间")

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="创建时间")

    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="更新时间")

    events: List[AgentEvent] = Field(default_factory=list, description="事件列表")

    files: List[FileInfo] = Field(default_factory=list, description="文件列表")

    status: SessionStatus = Field(default=SessionStatus.PENDING, description="会话状态")

    is_shared: bool = Field(default=False, description="是否共享")

    def get_last_plan(self) -> Optional[Plan]:
        """从事件中获取最后一个计划"""
        for event in reversed(self.events):
            if isinstance(event, PlanEvent):
                return event.plan
        return None
