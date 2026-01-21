from typing import Optional

from pydantic import BaseModel, Field

from manus_web_agent.domain.models.user import User


class AuthToken(BaseModel):
    """认证 Token"""

    access_token: str = Field(..., description="访问 Token")

    token_type: str = Field("bearer", description="Token 类型")

    refresh_token: Optional[str] = Field(None, description="刷新 Token")

    user: Optional[User] = Field(None, description="用户")
