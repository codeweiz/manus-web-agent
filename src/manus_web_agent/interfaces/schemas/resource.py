from pydantic import BaseModel, Field


class AccessTokenRequest(BaseModel):
    """访问令牌请求"""
    expire_minutes: int = Field(default=15, ge=1, le=15, description="过期时间（分钟）")


class SignedUrlResponse(BaseModel):
    """签名 URL 响应"""
    signed_url: str = Field(..., description="签名 URL")
    expires_in: int = Field(..., description="过期时间（秒）")
