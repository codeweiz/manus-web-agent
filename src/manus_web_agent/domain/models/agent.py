import uuid
from datetime import datetime, UTC
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator

from manus_web_agent.domain.models.memory import Memory


class Agent(BaseModel):
    """Agent 聚合根，管理 AI Agent 整个生命周期和状态，包括执行上下文、记忆、当前计划"""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16], description="Agent ID")
    user_id: str = Field(default="", description="用户 ID")
    memories: Dict[str, Memory] = Field(default_factory=dict, description="记忆")
    model_name: str = Field(default="", description="模型名")
    temperature: float = Field(default=0.7, description="温度")
    max_tokens: int = Field(default=1024, description="最大 token 数")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="更新时间")

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """验证温度比如在0-1之间"""
        if v < 0.0 or v > 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: Optional[int]) -> Optional[int]:
        """验证最大token必须为正数"""
        if v is not None and v <= 0:
            raise ValueError("Max tokens must be positive")
        return v

    class Config:
        arbitrary_types_allowed = True
