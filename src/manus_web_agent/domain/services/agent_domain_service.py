import logging
from datetime import datetime
from typing import Optional, AsyncGenerator, List, Type

from pydantic import TypeAdapter

from manus_web_agent.domain.external.file import FileStorage
from manus_web_agent.domain.external.llm import LLM
from manus_web_agent.domain.external.sandbox import Sandbox
from manus_web_agent.domain.external.search import SearchEngine
from manus_web_agent.domain.external.task import Task
from manus_web_agent.domain.models.event import BaseEvent, ErrorEvent, DoneEvent, MessageEvent, WaitEvent, AgentEvent
from manus_web_agent.domain.models.file import FileInfo
from manus_web_agent.domain.models.session import Session, SessionStatus
from manus_web_agent.domain.repositories.agent_repository import AgentRepository
from manus_web_agent.domain.repositories.mcp_repository import MCPRepository
from manus_web_agent.domain.repositories.session_repository import SessionRepository
from manus_web_agent.domain.services.agent_task_runner import AgentTaskRunner
from manus_web_agent.domain.utils.json_parser import JsonParser

logger = logging.getLogger(__name__)


class AgentDomainService:
    """Agent 领域服务"""

    def __init__(
            self,
            agent_repository: AgentRepository,
            session_repository: SessionRepository,
            llm: LLM,
            sandbox_cls: Type[Sandbox],
            task_cls: Type[Task],
            json_parser: JsonParser,
            file_storage: FileStorage,
            mcp_repository: MCPRepository,
            search_engine: Optional[SearchEngine] = None,
    ):
        self._agent_repository = agent_repository
        self._session_repository = session_repository
        self._llm = llm
        self._sandbox_cls = sandbox_cls
        self._task_cls = task_cls
        self._json_parser = json_parser
        self._file_storage = file_storage
        self._mcp_repository = mcp_repository
        self._search_engine = search_engine
        logger.info(f"AgentDomainService 初始化完成")

    async def shutdown(self):
        """关闭"""
        logger.info(f"开始关闭 AgentDomainService")
        await self._task_cls.destroy()
        logger.info(f"AgentDomainService 关闭完成")

    async def _create_task(self, session: Session) -> Task:
        """创建一个 agent 任务"""
        sandbox = None
        sandbox_id = session.sandbox_id
        if sandbox_id:
            sandbox = await self._sandbox_cls.get(sandbox_id)
        if not sandbox:
            sandbox = await self._sandbox_cls.create()
            session.sandbox_id = sandbox.id
            await self._session_repository.save(session)
        browser = await sandbox.get_browser()
        if not browser:
            logger.error(f"无法从沙箱获取浏览器: {sandbox.id}")
            raise RuntimeError(f"无法从沙箱获取浏览器: {sandbox.id}")

        await self._session_repository.save(session)

        task_runner = AgentTaskRunner(
            session_id=session.id,
            agent_id=session.agent_id,
            user_id=session.user_id,
            llm=self._llm,
            sandbox=sandbox,
            browser=browser,
            file_storage=self._file_storage,
            search_engine=self._search_engine,
            session_repository=self._session_repository,
            json_parser=self._json_parser,
            agent_repository=self._agent_repository,
            mcp_repository=self._mcp_repository,
        )

        task = self._task_cls.create(task_runner)
        session.task_id = task.id
        await self._session_repository.save(session)

        return task

    async def _get_task(self, session: Session) -> Optional[Task]:
        """获取任务"""
        task_id = session.task_id
        if not task_id:
            return None
        return self._task_cls.get(task_id)

    async def create_session(self, user_id: str) -> Session:
        """创建会话

        :param user_id: 用户 ID
        :return: 会话对象
        """
        # 创建或获取用户对应的 agent
        agent = await self._agent_repository.find_by_user_id(user_id)
        if not agent:
            from manus_web_agent.domain.models.agent import Agent
            agent = Agent(user_id=user_id)
            await self._agent_repository.save(agent)
            logger.info(f"为用户 {user_id} 创建新 Agent")

        # 创建会话
        session = Session(agent_id=agent.id, user_id=user_id)
        await self._session_repository.save(session)
        logger.info(f"创建会话 {session.id}，用户 {user_id}")

        return session

    async def get_session(self, session_id: str, user_id: str) -> Optional[Session]:
        """获取会话

        :param session_id: 会话 ID
        :param user_id: 用户 ID
        :return: 会话对象
        """
        return await self._session_repository.find_by_id_and_user_id(session_id, user_id)

    async def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """通过 ID 获取会话（不带用户验证）

        :param session_id: 会话 ID
        :return: 会话对象
        """
        return await self._session_repository.find_by_id(session_id)

    async def get_all_sessions(self, user_id: str) -> List[Session]:
        """获取用户的所有会话

        :param user_id: 用户 ID
        :return: 会话列表
        """
        return await self._session_repository.find_by_user_id(user_id)

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """删除会话

        :param session_id: 会话 ID
        :param user_id: 用户 ID
        :return: 是否成功
        """
        session = await self.get_session(session_id, user_id)
        if not session:
            return False

        # 停止任务
        await self.stop_session(session_id)

        # 删除会话
        await self._session_repository.delete(session_id)
        logger.info(f"删除会话 {session_id}")
        return True

    async def stop_session(self, session_id: str) -> None:
        """停止会话"""
        session = await self._session_repository.find_by_id(session_id)
        if not session:
            logger.error(f"尝试停止不存在的会话 {session_id}")
            raise RuntimeError("会话不存在")
        task = await self._get_task(session)
        if task:
            task.cancel()
        await self._session_repository.update_status(session_id, SessionStatus.COMPLETED)

    async def shell_view(self, session_id: str, shell_session_id: str) -> dict:
        """查看 Shell 输出

        :param session_id: 会话 ID
        :param shell_session_id: Shell 会话 ID
        :return: Shell 输出
        """
        session = await self._session_repository.find_by_id(session_id)
        if not session:
            raise RuntimeError("会话不存在")

        if not session.sandbox_id:
            return {"console": []}

        sandbox = await self._sandbox_cls.get(session.sandbox_id)
        if not sandbox:
            return {"console": []}

        result = await sandbox.view_shell(shell_session_id, console=True)
        if result.success and result.data:
            return {"console": result.data.get("console", [])}
        return {"console": []}

    async def file_view(self, session_id: str, file_path: str) -> dict:
        """查看文件内容

        :param session_id: 会话 ID
        :param file_path: 文件路径
        :return: 文件内容和信息
        """
        session = await self._session_repository.find_by_id(session_id)
        if not session:
            raise RuntimeError("会话不存在")

        if not session.sandbox_id:
            return {"content": None, "file": None}

        sandbox = await self._sandbox_cls.get(session.sandbox_id)
        if not sandbox:
            return {"content": None, "file": None}

        # 读取文件内容
        result = await sandbox.file_read(file_path)
        content = result.data.get("content") if result.success else None

        # 获取文件信息
        file_info = await self._session_repository.get_file_by_path(session_id, file_path)

        return {"content": content, "file": file_info}

    async def get_vnc_url(self, session_id: str) -> str:
        """获取 VNC URL

        :param session_id: 会话 ID
        :return: VNC WebSocket URL
        """
        session = await self._session_repository.find_by_id(session_id)
        if not session:
            raise RuntimeError("会话不存在")

        if not session.sandbox_id:
            raise RuntimeError("沙箱不存在")

        sandbox = await self._sandbox_cls.get(session.sandbox_id)
        if not sandbox:
            raise RuntimeError("沙箱不存在")

        return sandbox.vnc_url

    async def share_session(self, session_id: str) -> bool:
        """分享会话

        :param session_id: 会话 ID
        :return: 是否成功
        """
        await self._session_repository.update_shared_status(session_id, True)
        logger.info(f"分享会话 {session_id}")
        return True

    async def unshare_session(self, session_id: str) -> bool:
        """取消分享会话

        :param session_id: 会话 ID
        :return: 是否成功
        """
        await self._session_repository.update_shared_status(session_id, False)
        logger.info(f"取消分享会话 {session_id}")
        return True

    async def clear_unread_message_count(self, session_id: str, user_id: str) -> bool:
        """清除未读消息计数

        :param session_id: 会话 ID
        :param user_id: 用户 ID
        :return: 是否成功
        """
        await self._session_repository.update_unread_message_count(session_id, 0)
        return True

    async def chat(
            self,
            session_id: str,
            user_id: str,
            message: Optional[str] = None,
            timestamp: Optional[datetime] = None,
            latest_event_id: Optional[str] = None,
            attachments: Optional[List[dict]] = None
    ) -> AsyncGenerator[BaseEvent, None]:
        """与 Agent 聊天"""
        try:
            session = await self._session_repository.find_by_id_and_user_id(session_id, user_id)
            if not session:
                logger.error(f"尝试与不存在的会话 {session_id} 聊天，用户 {user_id}")
                raise RuntimeError("会话不存在")

            task = await self._get_task(session)

            if message:
                if session.status != SessionStatus.RUNNING:
                    task = await self._create_task(session)
                    if not task:
                        raise RuntimeError("创建任务失败")

                await self._session_repository.update_latest_message(session_id, message, timestamp or datetime.now())

                message_event = MessageEvent(
                    message=message,
                    role="user",
                    attachments=[FileInfo(file_id=attachment["file_id"], filename=attachment["filename"]) for attachment in attachments] if attachments else None
                )

                event_id = await task.input_stream.put(message_event.model_dump_json())

                message_event.id = event_id
                await self._session_repository.add_event(session_id, message_event)

                await task.run()
                logger.debug(f"将消息放入会话 {session_id} 的事件队列: {message[:50]}...")

            logger.info(f"会话 {session_id} 开始")
            logger.debug(f"会话 {session_id} 任务: {task}")

            while task and not task.done:
                event_id, event_str = await task.output_stream.get(start_id=latest_event_id, block_ms=0)
                latest_event_id = event_id
                if event_str is None:
                    logger.debug(f"会话 {session_id} 的事件队列中没有事件")
                    continue
                event = TypeAdapter(AgentEvent).validate_json(event_str)
                event.id = event_id
                logger.debug(f"从会话 {session_id} 的事件队列获取事件: {type(event).__name__}")
                await self._session_repository.update_unread_message_count(session_id, 0)
                yield event
                if isinstance(event, (DoneEvent, ErrorEvent, WaitEvent)):
                    break

            logger.info(f"会话 {session_id} 完成")

        except Exception as e:
            logger.exception(f"会话 {session_id} 发生错误")
            event = ErrorEvent(error=str(e))
            await self._session_repository.add_event(session_id, event)
            yield event
        finally:
            await self._session_repository.update_unread_message_count(session_id, 0)
