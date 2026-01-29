from typing import AsyncGenerator, List, Optional
import logging

from manus_web_agent.domain.models.event import BaseEvent, PlanEvent, PlanStatus, MessageEvent
from manus_web_agent.domain.models.message import Message
from manus_web_agent.domain.models.plan import Plan, Step
from manus_web_agent.domain.repositories.agent_repository import AgentRepository
from manus_web_agent.domain.services.agents.base import BaseAgent
from manus_web_agent.domain.services.prompts.system import SYSTEM_PROMPT
from manus_web_agent.domain.services.prompts.planner import CREATE_PLAN_PROMPT, UPDATE_PLAN_PROMPT, PLANNER_SYSTEM_PROMPT
from manus_web_agent.domain.services.tools.base import BaseTool
from manus_web_agent.domain.external.llm import LLM
from manus_web_agent.domain.utils.json_parser import JsonParser

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """规划代理类，定义规划的基本行为"""

    name: str = "planner"
    system_prompt: str = SYSTEM_PROMPT + PLANNER_SYSTEM_PROMPT
    format: Optional[str] = "json_object"
    tool_choice: Optional[str] = "none"

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
            tools=tools,
        )

    async def create_plan(self, message: Message) -> AsyncGenerator[BaseEvent, None]:
        """创建计划"""
        prompt = CREATE_PLAN_PROMPT.format(
            message=message.message,
            attachments="\n".join(message.attachments)
        )
        async for event in self.execute(prompt):
            if isinstance(event, MessageEvent):
                logger.info(event.message)
                parsed_response = await self._json_parser.parse(event.message)
                plan = Plan.model_validate(parsed_response)
                yield PlanEvent(status=PlanStatus.CREATED, plan=plan)
            else:
                yield event

    async def update_plan(self, plan: Plan, step: Step) -> AsyncGenerator[BaseEvent, None]:
        """更新计划"""
        prompt = UPDATE_PLAN_PROMPT.format(plan=plan.dump_json(), step=step.model_dump_json())
        async for event in self.execute(prompt):
            if isinstance(event, MessageEvent):
                logger.debug(f"规划代理更新计划: {event.message}")
                parsed_response = await self._json_parser.parse(event.message)
                updated_plan = Plan.model_validate(parsed_response)
                new_steps = [Step.model_validate(s) for s in updated_plan.steps]

                # 找到第一个待处理步骤的索引
                first_pending_index = None
                for i, s in enumerate(plan.steps):
                    if not s.is_done():
                        first_pending_index = i
                        break

                # 如果有待处理步骤，替换所有待处理步骤
                if first_pending_index is not None:
                    # 保留已完成步骤
                    updated_steps = plan.steps[:first_pending_index]
                    # 添加新步骤
                    updated_steps.extend(new_steps)
                    # 更新计划中的步骤
                    plan.steps = updated_steps

                yield PlanEvent(status=PlanStatus.UPDATED, plan=plan)
            else:
                yield event
