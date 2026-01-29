from typing import AsyncGenerator, List, Optional
import logging

from manus_web_agent.domain.models.event import (
    BaseEvent, StepEvent, StepStatus, ErrorEvent, MessageEvent, ToolEvent, ToolStatus, WaitEvent
)
from manus_web_agent.domain.models.file import FileInfo
from manus_web_agent.domain.models.message import Message
from manus_web_agent.domain.models.plan import Plan, Step, ExecutionStatus
from manus_web_agent.domain.repositories.agent_repository import AgentRepository
from manus_web_agent.domain.services.agents.base import BaseAgent
from manus_web_agent.domain.services.prompts.system import SYSTEM_PROMPT
from manus_web_agent.domain.services.prompts.execution import EXECUTION_SYSTEM_PROMPT, EXECUTION_PROMPT, SUMMARIZE_PROMPT
from manus_web_agent.domain.services.tools.base import BaseTool
from manus_web_agent.domain.external.llm import LLM
from manus_web_agent.domain.utils.json_parser import JsonParser

logger = logging.getLogger(__name__)


class ExecutionAgent(BaseAgent):
    """执行代理类，定义执行的基本行为"""

    name: str = "execution"
    system_prompt: str = SYSTEM_PROMPT + EXECUTION_SYSTEM_PROMPT
    format: str = "json_object"

    def __init__(
            self,
            agent_id: str,
            agent_repository: AgentRepository,
            llm: LLM,
            tools: List[BaseTool],
            json_parser: JsonParser,
    ):
        super().__init__(
            agent_id=agent_id,
            agent_repository=agent_repository,
            llm=llm,
            json_parser=json_parser,
            tools=tools
        )

    async def execute_step(self, plan: Plan, step: Step, message: Message) -> AsyncGenerator[BaseEvent, None]:
        """执行步骤"""
        prompt = EXECUTION_PROMPT.format(
            step=step.description,
            message=message.message,
            attachments="\n".join(message.attachments),
            language=plan.language
        )
        step.status = ExecutionStatus.RUNNING
        yield StepEvent(status=StepStatus.STARTED, step=step)
        async for event in self.execute(prompt):
            if isinstance(event, ErrorEvent):
                step.status = ExecutionStatus.FAILED
                step.error = event.error
                yield StepEvent(status=StepStatus.FAILED, step=step)
            elif isinstance(event, MessageEvent):
                step.status = ExecutionStatus.COMPLETED
                parsed_response = await self._json_parser.parse(event.message)
                new_step = Step.model_validate(parsed_response)
                step.success = new_step.success
                step.result = new_step.result
                step.attachments = new_step.attachments
                yield StepEvent(status=StepStatus.COMPLETED, step=step)
                if step.result:
                    yield MessageEvent(message=step.result)
                continue
            elif isinstance(event, ToolEvent):
                if event.function_name == "message_ask_user":
                    if event.status == ToolStatus.CALLING:
                        yield MessageEvent(message=event.function_args.get("text", ""))
                    elif event.status == ToolStatus.CALLED:
                        yield WaitEvent()
                        return
                    continue
            yield event
        step.status = ExecutionStatus.COMPLETED

    async def summarize(self) -> AsyncGenerator[BaseEvent, None]:
        """总结任务"""
        async for event in self.execute(SUMMARIZE_PROMPT):
            if isinstance(event, MessageEvent):
                logger.debug(f"执行代理总结: {event.message}")
                parsed_response = await self._json_parser.parse(event.message)
                message = Message.model_validate(parsed_response)
                attachments = [FileInfo(file_path=file_path) for file_path in message.attachments]
                yield MessageEvent(message=message.message, attachments=attachments)
                continue
            yield event
