"""Agent 应用服务"""

import logging
from datetime import datetime
from typing import AsyncGenerator, List, Optional

from manus_web_agent.application.errors.exceptions import NotFoundError, UnauthorizedError
from manus_web_agent.application.services.token_service import TokenService
from manus_web_agent.domain.models.event import AgentEvent
from manus_web_agent.domain.models.file import FileInfo
from manus_web_agent.domain.models.session import Session, SessionStatus
from manus_web_agent.domain.services.agent_domain_service import AgentDomainService

logger = logging.getLogger(__name__)


class AgentService:
    """Agent 应用服务，封装领域服务，提供会话管理、聊天、文件查看等功能"""

    def __init__(
        self,
        agent_domain_service: AgentDomainService,
        token_service: TokenService,
    ):
        self._agent_domain_service = agent_domain_service
        self._token_service = token_service

    async def create_session(self, user_id: str) -> Session:
        """创建会话

        :param user_id: 用户 ID
        :return: 会话对象
        """
        return await self._agent_domain_service.create_session(user_id)

    async def get_session(self, session_id: str, user_id: str) -> Optional[Session]:
        """获取会话

        :param session_id: 会话 ID
        :param user_id: 用户 ID
        :return: 会话对象
        """
        return await self._agent_domain_service.get_session(session_id, user_id)

    async def get_all_sessions(self, user_id: str) -> List[Session]:
        """获取用户的所有会话

        :param user_id: 用户 ID
        :return: 会话列表
        """
        return await self._agent_domain_service.get_all_sessions(user_id)

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """删除会话

        :param session_id: 会话 ID
        :param user_id: 用户 ID
        :return: 是否成功
        """
        return await self._agent_domain_service.delete_session(session_id, user_id)

    async def stop_session(self, session_id: str, user_id: str) -> bool:
        """停止会话

        :param session_id: 会话 ID
        :param user_id: 用户 ID
        :return: 是否成功
        """
        session = await self.get_session(session_id, user_id)
        if not session:
            raise NotFoundError("会话不存在")

        await self._agent_domain_service.stop_session(session_id)
        return True

    async def chat(
        self,
        session_id: str,
        user_id: str,
        message: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        event_id: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """聊天

        :param session_id: 会话 ID
        :param user_id: 用户 ID
        :param message: 消息内容
        :param timestamp: 时间戳
        :param event_id: 事件 ID（用于断点续传）
        :param attachments: 附件列表
        :return: 事件流
        """
        session = await self.get_session(session_id, user_id)
        if not session:
            raise NotFoundError("会话不存在")

        async for event in self._agent_domain_service.chat(
            session_id=session_id,
            user_id=user_id,
            message=message,
            timestamp=timestamp,
            latest_event_id=event_id,
            attachments=attachments,
        ):
            yield event

    async def shell_view(self, session_id: str, shell_session_id: str, user_id: str) -> dict:
        """查看 Shell 输出

        :param session_id: 会话 ID
        :param shell_session_id: Shell 会话 ID
        :param user_id: 用户 ID
        :return: Shell 输出
        """
        session = await self.get_session(session_id, user_id)
        if not session:
            raise NotFoundError("会话不存在")

        return await self._agent_domain_service.shell_view(
            session_id, shell_session_id
        )

    async def file_view(self, session_id: str, file_path: str, user_id: str) -> dict:
        """查看文件内容

        :param session_id: 会话 ID
        :param file_path: 文件路径
        :param user_id: 用户 ID
        :return: 文件内容
        """
        session = await self.get_session(session_id, user_id)
        if not session:
            raise NotFoundError("会话不存在")

        return await self._agent_domain_service.file_view(session_id, file_path)

    async def get_vnc_url(self, session_id: str, user_id: Optional[str] = None) -> str:
        """获取 VNC URL

        :param session_id: 会话 ID
        :param user_id: 用户 ID（可选）
        :return: VNC WebSocket URL
        """
        if user_id:
            session = await self.get_session(session_id, user_id)
        else:
            session = await self._agent_domain_service.get_session_by_id(session_id)

        if not session:
            raise NotFoundError("会话不存在")

        return await self._agent_domain_service.get_vnc_url(session_id)

    async def share_session(self, session_id: str, user_id: str) -> bool:
        """分享会话

        :param session_id: 会话 ID
        :param user_id: 用户 ID
        :return: 是否成功
        """
        session = await self.get_session(session_id, user_id)
        if not session:
            raise NotFoundError("会话不存在")

        if session.user_id != user_id:
            raise UnauthorizedError("无权操作此会话")

        return await self._agent_domain_service.share_session(session_id)

    async def unshare_session(self, session_id: str, user_id: str) -> bool:
        """取消分享会话

        :param session_id: 会话 ID
        :param user_id: 用户 ID
        :return: 是否成功
        """
        session = await self.get_session(session_id, user_id)
        if not session:
            raise NotFoundError("会话不存在")

        if session.user_id != user_id:
            raise UnauthorizedError("无权操作此会话")

        return await self._agent_domain_service.unshare_session(session_id)

    async def is_session_shared(self, session_id: str) -> bool:
        """检查会话是否已分享

        :param session_id: 会话 ID
        :return: 是否已分享
        """
        session = await self._agent_domain_service.get_session_by_id(session_id)
        if not session:
            return False
        return session.is_shared

    async def get_shared_session(self, session_id: str) -> Optional[Session]:
        """获取共享会话（无需认证）

        :param session_id: 会话 ID
        :return: 会话对象
        """
        session = await self._agent_domain_service.get_session_by_id(session_id)
        if not session or not session.is_shared:
            return None
        return session

    async def get_session_files(
        self, session_id: str, user_id: Optional[str] = None
    ) -> List[FileInfo]:
        """获取会话文件列表

        :param session_id: 会话 ID
        :param user_id: 用户 ID（可选）
        :return: 文件列表
        """
        if user_id:
            session = await self.get_session(session_id, user_id)
        else:
            session = await self._agent_domain_service.get_session_by_id(session_id)

        if not session:
            raise NotFoundError("会话不存在")

        return session.files or []

    async def get_shared_session_files(self, session_id: str) -> List[FileInfo]:
        """获取共享会话的文件列表

        :param session_id: 会话 ID
        :return: 文件列表
        """
        session = await self.get_shared_session(session_id)
        if not session:
            raise NotFoundError("共享会话不存在")

        return session.files or []

    async def clear_unread_message_count(self, session_id: str, user_id: str) -> bool:
        """清除未读消息计数

        :param session_id: 会话 ID
        :param user_id: 用户 ID
        :return: 是否成功
        """
        session = await self.get_session(session_id, user_id)
        if not session:
            raise NotFoundError("会话不存在")

        return await self._agent_domain_service.clear_unread_message_count(
            session_id, user_id
        )
