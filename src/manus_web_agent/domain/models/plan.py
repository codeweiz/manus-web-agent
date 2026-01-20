import uuid
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """执行状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Step(BaseModel):
    """步骤"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="步骤 ID")

    description: str = Field(..., description="描述")

    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="状态")

    result: Optional[str] = Field(default=None, description="结果")

    error: Optional[str] = Field(default=None, description="错误信息")

    success: Optional[bool] = Field(default=None, description="是否成功")

    attachments: Optional[List[str]] = Field(default=None, description="附件")

    def is_done(self) -> bool:
        """是否已完成"""
        return self.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]


class Plan(BaseModel):
    """计划"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="计划 ID")

    title: str = Field(..., description="标题")

    goal: str = Field(..., description="目标")

    language: str = Field(default="en", description="语言")

    steps: List[Step] = Field(default_factory=list, description="步骤列表")

    message: Optional[str] = Field(default=None, description="消息")

    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="状态")

    result: Optional[Dict[str, Any]] = Field(default=None, description="结果")

    error: Optional[str] = Field(default=None, description="错误信息")

    def is_done(self) -> bool:
        """是否已完成"""
        return self.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]

    def get_next_step(self) -> Optional[Step]:
        """获取下一个步骤"""
        for step in self.steps:
            if not step.is_done():
                return step
        return None

    def dump_json(self) -> str:
        """导出 JSON"""
        return self.model_dump_json(include={"goal", "language", "steps"})
