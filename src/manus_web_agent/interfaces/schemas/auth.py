"""认证相关 Schema"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from manus_web_agent.domain.models.user import User, UserRole


class LoginRequest(BaseModel):
    """登录请求"""

    email: str = Field(..., description="邮箱")
    password: str = Field(..., description="密码")


class RegisterRequest(BaseModel):
    """注册请求"""

    fullname: str = Field(..., min_length=2, description="用户全名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, description="密码")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """验证邮箱格式"""
        if "@" not in v:
            raise ValueError("无效的邮箱地址")
        return v.lower()


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""

    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")


class ChangeFullnameRequest(BaseModel):
    """修改姓名请求"""

    new_fullname: str = Field(..., min_length=2, description="新姓名")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""

    refresh_token: str = Field(..., description="刷新令牌")


class SendVerificationCodeRequest(BaseModel):
    """发送验证码请求"""

    email: str = Field(..., description="邮箱")


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""

    email: str = Field(..., description="邮箱")
    code: str = Field(..., pattern=r"^\d{6}$", description="验证码")
    new_password: str = Field(..., min_length=6, description="新密码")


class UserResponse(BaseModel):
    """用户响应"""

    user_id: str = Field(..., description="用户 ID")
    email: str = Field(..., description="邮箱")
    fullname: str = Field(..., description="用户全名")
    role: str = Field(..., description="角色")
    is_active: bool = Field(..., description="是否激活")

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        """从用户领域模型创建响应"""
        return cls(
            user_id=user.id,
            email=user.email,
            fullname=user.fullname,
            role=user.role.value,
            is_active=user.is_active,
        )


class LoginResponse(BaseModel):
    """登录响应"""

    user: UserResponse = Field(..., description="用户信息")
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")


class RegisterResponse(BaseModel):
    """注册响应"""

    user: UserResponse = Field(..., description="用户信息")
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")


class AuthStatusResponse(BaseModel):
    """认证状态响应"""

    enabled: bool = Field(..., description="是否启用认证")
    provider: str = Field(..., description="认证提供者")


class RefreshTokenResponse(BaseModel):
    """刷新令牌响应"""

    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
