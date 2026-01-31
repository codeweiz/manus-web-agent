import logging
from enum import Enum
from typing import AsyncGenerator, Optional

from manus_web_agent.domain.external.browser import Browser
from manus_web_agent.domain.external.llm import LLM
from manus_web_agent.domain.external.sandbox import Sandbox
from manus_web_agent.domain.external.search import SearchEngine
from manus_web_agent.domain.models.event import (
    BaseEvent, PlanEvent, PlanStatus, MessageEvent, DoneEvent, TitleEvent
)
from manus_web_agent.domain.models.message import Message
from manus_web_agent.domain.models.plan import ExecutionStatus
from manus_web_agent.domain.models.session import SessionStatus
from manus_web_agent.domain.repositories.agent_repository import AgentRepository
from manus_web_agent.domain.repositories.session_repository import SessionRepository
from manus_web_agent.domain.services.agents.execution import ExecutionAgent
from manus_web_agent.domain.services.agents.planner import PlannerAgent
from manus_web_agent.domain.services.flows.base import BaseFlow
from manus_web_agent.domain.services.tools.browser import BrowserTool
from manus_web_agent.domain.services.tools.file import FileTool
from manus_web_agent.domain.services.tools.mcp import MCPTool
from manus_web_agent.domain.services.tools.message import MessageTool
from manus_web_agent.domain.services.tools.search import SearchTool
from manus_web_agent.domain.services.tools.shell import ShellTool
from manus_web_agent.domain.utils.json_parser import JsonParser

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent 状态"""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    UPDATING = "updating"


class PlanActFlow(BaseFlow):
    """计划-执行流程"""

    def __init__(
            self,
            agent_id: str,
            agent_repository: AgentRepository,
            session_id: str,
            session_repository: SessionRepository,
            llm: LLM,
            sandbox: Sandbox,
            browser: Browser,
            json_parser: JsonParser,
            mcp_tool: MCPTool,
            search_engine: Optional[SearchEngine] = None,
    ):
        self._agent_id = agent_id
        self._agent_repository = agent_repository
        self._session_id = session_id
        self._session_repository = session_repository
        self.status = AgentStatus.IDLE
        self.plan = None

        tools = [
            ShellTool(sandbox),
            BrowserTool(browser),
            FileTool(sandbox),
            MessageTool(),
            mcp_tool
        ]

        # 只在有搜索引擎时添加搜索工具
        if search_engine:
            tools.append(SearchTool(search_engine))

        # 创建规划代理和执行代理
        self.planner = PlannerAgent(
            agent_id=self._agent_id,
            agent_repository=self._agent_repository,
            llm=llm,
            tools=tools,
            json_parser=json_parser,
        )
        logger.debug(f"为 Agent {self._agent_id} 创建规划代理")

        self.executor = ExecutionAgent(
            agent_id=self._agent_id,
            agent_repository=self._agent_repository,
            llm=llm,
            tools=tools,
            json_parser=json_parser,
        )
        logger.debug(f"为 Agent {self._agent_id} 创建执行代理")

    async def run(self, message: Message) -> AsyncGenerator[BaseEvent, None]:
        # 获取会话并检查状态，根据状态决定执行流程
        session = await self._session_repository.find_by_id(self._session_id)
        if not session:
            raise ValueError(f"会话 {self._session_id} 不存在")

        if session.status != SessionStatus.PENDING:
            logger.debug(f"会话 {self._session_id} 不在 PENDING 状态，回滚")
            await self.executor.roll_back(message)
            await self.planner.roll_back(message)

        if session.status == SessionStatus.RUNNING:
            logger.debug(f"会话 {self._session_id} 在 RUNNING 状态")
            self.status = AgentStatus.PLANNING

        if session.status == SessionStatus.WAITING:
            logger.debug(f"会话 {self._session_id} 在 WAITING 状态")
            self.status = AgentStatus.EXECUTING

        await self._session_repository.update_status(self._session_id, SessionStatus.RUNNING)
        self.plan = session.get_last_plan()

        logger.info(f"Agent {self._agent_id} 开始处理消息: {message.message[:50]}...")
        step = None
        while True:
            if self.status == AgentStatus.IDLE:
                logger.info(f"Agent {self._agent_id} 状态从 {AgentStatus.IDLE} 变为 {AgentStatus.PLANNING}")
                self.status = AgentStatus.PLANNING
            elif self.status == AgentStatus.PLANNING:
                # 创建计划
                logger.info(f"Agent {self._agent_id} 开始创建计划")
                async for event in self.planner.create_plan(message):
                    if isinstance(event, PlanEvent) and event.status == PlanStatus.CREATED:
                        self.plan = event.plan
                        logger.info(f"Agent {self._agent_id} 成功创建计划，包含 {len(event.plan.steps)} 个步骤")
                        yield TitleEvent(title=event.plan.title)
                        yield MessageEvent(role="assistant", message=event.plan.message)
                    yield event
                logger.info(f"Agent {self._agent_id} 状态从 {AgentStatus.PLANNING} 变为 {AgentStatus.EXECUTING}")
                self.status = AgentStatus.EXECUTING
                if len(event.plan.steps) == 0:
                    logger.info(f"Agent {self._agent_id} 创建的计划没有步骤")
                    self.status = AgentStatus.COMPLETED

            elif self.status == AgentStatus.EXECUTING:
                # 执行计划
                self.plan.status = ExecutionStatus.RUNNING
                step = self.plan.get_next_step()
                if not step:
                    logger.info(f"Agent {self._agent_id} 没有更多步骤，状态从 {AgentStatus.EXECUTING} 变为 {AgentStatus.COMPLETED}")
                    self.status = AgentStatus.SUMMARIZING
                    continue
                # 执行步骤
                logger.info(f"Agent {self._agent_id} 开始执行步骤 {step.id}: {step.description[:50]}...")
                async for event in self.executor.execute_step(self.plan, step, message):
                    yield event
                logger.info(f"Agent {self._agent_id} 完成步骤 {step.id}，状态从 {AgentStatus.EXECUTING} 变为 {AgentStatus.UPDATING}")
                await self.executor.compact_memory()
                logger.debug(f"Agent {self._agent_id} 压缩记忆")
                self.status = AgentStatus.UPDATING
            elif self.status == AgentStatus.UPDATING:
                # 更新计划
                logger.info(f"Agent {self._agent_id} 开始更新计划")
                async for event in self.planner.update_plan(self.plan, step):
                    yield event
                logger.info(f"Agent {self._agent_id} 计划更新完成，状态从 {AgentStatus.UPDATING} 变为 {AgentStatus.EXECUTING}")
                self.status = AgentStatus.EXECUTING
            elif self.status == AgentStatus.SUMMARIZING:
                # 总结
                logger.info(f"Agent {self._agent_id} 开始总结")
                async for event in self.executor.summarize():
                    yield event
                logger.info(f"Agent {self._agent_id} 总结完成，状态从 {AgentStatus.SUMMARIZING} 变为 {AgentStatus.COMPLETED}")
                self.status = AgentStatus.COMPLETED
            elif self.status == AgentStatus.COMPLETED:
                self.plan.status = ExecutionStatus.COMPLETED
                logger.info(f"Agent {self._agent_id} 计划已完成")
                yield PlanEvent(status=PlanStatus.COMPLETED, plan=self.plan)
                self.status = AgentStatus.IDLE
                break
        yield DoneEvent()

        logger.info(f"Agent {self._agent_id} 消息处理完成")

    def is_done(self) -> bool:
        return self.status == AgentStatus.IDLE
