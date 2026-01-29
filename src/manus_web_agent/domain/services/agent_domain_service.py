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
