from datetime import datetime
from typing import Protocol, Optional

from manus_web_agent.domain.models.event import BaseEvent
from manus_web_agent.domain.models.file import FileInfo
from manus_web_agent.domain.models.session import Session, SessionStatus


class SessionRepository(Protocol):
    """Session Repository"""

    async def save(self, session: Session) -> None:
        """保存或更新 Session"""
        pass

    async def find_by_id(self, session_id: str) -> Optional[Session]:
        """根据 ID 查找 Session"""
        pass

    async def find_by_user_id(self, user_id: str) -> list[Session]:
        """根据用户 ID 查找 Session"""
        pass

    async def find_by_id_and_user_id(self, session_id: str, user_id: str) -> Optional[Session]:
        """根据 ID 和用户 ID 查找 Session"""
        pass

    async def update_title(self, session_id: str, title: str) -> None:
        """更新 Session 标题"""
        pass

    async def update_latest_message(self, session_id: str, message: str, timestamp: datetime) -> None:
        """更新 Session 最新消息"""
        pass

    async def add_event(self, session_id: str, event: BaseEvent) -> None:
        """为 Session 添加事件"""
        pass

    async def add_file(self, session_id: str, file: FileInfo) -> None:
        """为 Session 添加文件"""
        pass

    async def remove_file(self, session_id: str, file_id: str) -> None:
        """为 Session 移除文件"""
        pass

    async def get_file_by_path(self, session_id: str, file_path: str) -> Optional[FileInfo]:
        """根据文件路径获取 Session 文件"""
        pass

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        """更新 Session 状态"""
        pass

    async def update_unread_message_count(self, session_id: str, unread_message_count: int) -> None:
        """更新 Session 未读消息数"""
        pass

    async def increment_unread_message_count(self, session_id: str) -> None:
        """增加 Session 未读消息数"""
        pass

    async def decrement_unread_message_count(self, session_id: str) -> None:
        """减少 Session 未读消息数"""
        pass

    async def update_shared_status(self, session_id: str, is_shared: bool) -> None:
        """更新 Session 共享状态"""
        pass

    async def delete(self, session_id: str) -> None:
        """删除 Session"""
        pass

    async def get_all(self) -> list[Session]:
        """获取所有 Session"""
        pass
