from datetime import datetime, UTC
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserRole(str, Enum):
    """用户角色"""

    ADMIN = "admin"
    USER = "user"


class User(BaseModel):
    """用户"""

    id: str = Field(..., description="用户 ID")
    fullname: str = Field(..., description="用户全名")
    email: str = Field(..., description="邮箱")
    password_hash: Optional[str] = Field(default=None, description="密码哈希")
    role: UserRole = Field(default=UserRole.USER, description="用户角色")
    is_active: bool = Field(default=True, description="是否激活")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="更新时间")
    last_login_at: Optional[datetime] = Field(default=None, description="最后登录时间")

    @field_validator("fullname")
    @classmethod
    def validate_fullname(cls, v):
        """验证全名"""
        if not v or len(v.strip()) < 2:
            raise ValueError("Fullname must be at least 2 characters long")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        """验证邮箱"""
        if not v or "@" not in v:
            raise ValueError("Invalid email address")
        return v.strip().lower()

    def update_last_login(self):
        """更新上次更新时间"""
        self.last_login_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def deactivate(self):
        """禁用用户"""
        self.is_active = False
        self.updated_at = datetime.now(UTC)

    def activate(self):
        """激活用户"""
        self.is_active = True
        self.updated_at = datetime.now(UTC)
