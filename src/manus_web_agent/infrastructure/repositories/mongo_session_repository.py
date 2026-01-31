"""Session MongoDB 仓库实现"""

import logging
from datetime import datetime
from typing import List, Optional

from manus_web_agent.domain.models.event import BaseEvent
from manus_web_agent.domain.models.file import FileInfo
from manus_web_agent.domain.models.session import Session, SessionStatus
from manus_web_agent.domain.repositories.session_repository import SessionRepository
from manus_web_agent.infrastructure.models.documents import SessionDocument

logger = logging.getLogger(__name__)


class MongoSessionRepository(SessionRepository):
    """Session MongoDB 仓库"""

    async def save(self, session: Session) -> None:
        """保存或更新 Session"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session.id)
        if doc:
            # 更新现有文档
            doc.agent_id = session.agent_id
            doc.user_id = session.user_id
            doc.title = session.title
            doc.status = session.status.value
            doc.events = [event.model_dump() for event in session.events] if session.events else []
            doc.files = [file.model_dump() for file in session.files] if session.files else []
            doc.is_shared = session.is_shared
            doc.sandbox_id = session.sandbox_id
            doc.task_id = session.task_id
            doc.latest_message = session.latest_message
            doc.latest_message_at = session.latest_message_at
            doc.unread_message_count = session.unread_message_count
            await doc.save()
        else:
            # 创建新文档
            doc = SessionDocument.from_domain(session)
            await doc.insert()
        logger.debug(f"保存 Session {session.id}")

    async def find_by_id(self, session_id: str) -> Optional[Session]:
        """根据 ID 查找 Session"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        return doc.to_domain() if doc else None

    async def find_by_user_id(self, user_id: str) -> List[Session]:
        """根据用户 ID 查找 Session"""
        docs = await SessionDocument.find(SessionDocument.user_id == user_id).to_list()
        return [doc.to_domain() for doc in docs]

    async def find_by_id_and_user_id(self, session_id: str, user_id: str) -> Optional[Session]:
        """根据 ID 和用户 ID 查找 Session"""
        doc = await SessionDocument.find_one(
            SessionDocument.session_id == session_id,
            SessionDocument.user_id == user_id
        )
        return doc.to_domain() if doc else None

    async def update_title(self, session_id: str, title: str) -> None:
        """更新 Session 标题"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        if doc:
            doc.title = title
            await doc.save()
            logger.debug(f"更新 Session {session_id} 标题: {title}")

    async def update_latest_message(self, session_id: str, message: str, timestamp: datetime) -> None:
        """更新 Session 最新消息"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        if doc:
            doc.latest_message = message
            doc.latest_message_at = timestamp
            await doc.save()
            logger.debug(f"更新 Session {session_id} 最新消息")

    async def add_event(self, session_id: str, event: BaseEvent) -> None:
        """为 Session 添加事件"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        if doc:
            if doc.events is None:
                doc.events = []
            doc.events.append(event.model_dump())
            await doc.save()
            logger.debug(f"为 Session {session_id} 添加事件")

    async def add_file(self, session_id: str, file: FileInfo) -> None:
        """为 Session 添加文件"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        if doc:
            if doc.files is None:
                doc.files = []
            doc.files.append(file.model_dump())
            await doc.save()
            logger.debug(f"为 Session {session_id} 添加文件 {file.file_id}")

    async def remove_file(self, session_id: str, file_id: str) -> None:
        """为 Session 移除文件"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        if doc and doc.files:
            doc.files = [f for f in doc.files if f.get("file_id") != file_id]
            await doc.save()
            logger.debug(f"为 Session {session_id} 移除文件 {file_id}")

    async def get_file_by_path(self, session_id: str, file_path: str) -> Optional[FileInfo]:
        """根据文件路径获取 Session 文件"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        if doc and doc.files:
            for file_data in doc.files:
                if file_data.get("file_path") == file_path:
                    return FileInfo(**file_data)
        return None

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        """更新 Session 状态"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        if doc:
            doc.status = status.value
            await doc.save()
            logger.debug(f"更新 Session {session_id} 状态: {status.value}")

    async def update_unread_message_count(self, session_id: str, unread_message_count: int) -> None:
        """更新 Session 未读消息数"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        if doc:
            doc.unread_message_count = unread_message_count
            await doc.save()

    async def increment_unread_message_count(self, session_id: str) -> None:
        """增加 Session 未读消息数"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        if doc:
            doc.unread_message_count = (doc.unread_message_count or 0) + 1
            await doc.save()

    async def decrement_unread_message_count(self, session_id: str) -> None:
        """减少 Session 未读消息数"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        if doc:
            doc.unread_message_count = max(0, (doc.unread_message_count or 0) - 1)
            await doc.save()

    async def update_shared_status(self, session_id: str, is_shared: bool) -> None:
        """更新 Session 共享状态"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        if doc:
            doc.is_shared = is_shared
            await doc.save()
            logger.debug(f"更新 Session {session_id} 共享状态: {is_shared}")

    async def delete(self, session_id: str) -> None:
        """删除 Session"""
        doc = await SessionDocument.find_one(SessionDocument.session_id == session_id)
        if doc:
            await doc.delete()
            logger.debug(f"删除 Session {session_id}")

    async def get_all(self) -> List[Session]:
        """获取所有 Session"""
        docs = await SessionDocument.find_all().to_list()
        return [doc.to_domain() for doc in docs]
