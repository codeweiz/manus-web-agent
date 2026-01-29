from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from manus_web_agent.domain.models.session import SessionStatus


class ChatRequest(BaseModel):
    """聊天请求"""
    message: Optional[str] = Field(default=None, description="消息内容")
    attachments: Optional[List[dict]] = Field(default=None, description="附件列表")
    event_id: Optional[str] = Field(default=None, description="事件 ID")
    timestamp: Optional[int] = Field(default=None, description="时间戳")


class ShellViewRequest(BaseModel):
    """Shell 查看请求"""
    session_id: str = Field(..., description="Shell 会话 ID")


class CreateSessionResponse(BaseModel):
    """创建会话响应"""
    session_id: str = Field(..., description="会话 ID")


class GetSessionResponse(BaseModel):
    """获取会话响应"""
    session_id: str = Field(..., description="会话 ID")
    title: Optional[str] = Field(default=None, description="会话标题")
    status: SessionStatus = Field(..., description="会话状态")
    events: List[dict] = Field(default_factory=list, description="事件列表")
    is_shared: bool = Field(default=False, description="是否已分享")


class ListSessionItem(BaseModel):
    """会话列表项"""
    session_id: str = Field(..., description="会话 ID")
    title: Optional[str] = Field(default=None, description="会话标题")
    status: SessionStatus = Field(..., description="会话状态")
    unread_message_count: int = Field(default=0, description="未读消息数")
    latest_message: Optional[str] = Field(default=None, description="最新消息")
    latest_message_at: Optional[int] = Field(default=None, description="最新消息时间")
    is_shared: bool = Field(default=False, description="是否已分享")


class ListSessionResponse(BaseModel):
    """会话列表响应"""
    sessions: List[ListSessionItem] = Field(default_factory=list, description="会话列表")


class ConsoleRecord(BaseModel):
    """控制台记录"""
    ps1: str = Field(..., description="提示符")
    command: Optional[str] = Field(default=None, description="命令")
    output: Optional[str] = Field(default=None, description="输出")


class ShellViewResponse(BaseModel):
    """Shell 查看响应"""
    console: List[ConsoleRecord] = Field(default_factory=list, description="控制台记录")


class ShareSessionResponse(BaseModel):
    """分享会话响应"""
    session_id: str = Field(..., description="会话 ID")
    is_shared: bool = Field(..., description="是否已分享")


class SharedSessionResponse(BaseModel):
    """共享会话响应"""
    session_id: str = Field(..., description="会话 ID")
    title: Optional[str] = Field(default=None, description="会话标题")
    status: SessionStatus = Field(..., description="会话状态")
    events: List[dict] = Field(default_factory=list, description="事件列表")
    is_shared: bool = Field(..., description="是否已分享")
