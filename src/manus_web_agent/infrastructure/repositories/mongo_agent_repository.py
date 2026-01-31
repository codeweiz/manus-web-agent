"""Agent MongoDB 仓库实现"""

import logging
from typing import Optional

from manus_web_agent.domain.models.agent import Agent
from manus_web_agent.domain.models.memory import Memory
from manus_web_agent.domain.repositories.agent_repository import AgentRepository
from manus_web_agent.infrastructure.models.documents import AgentDocument

logger = logging.getLogger(__name__)


class MongoAgentRepository(AgentRepository):
    """Agent MongoDB 仓库"""

    async def save(self, agent: Agent) -> None:
        """保存或更新 Agent"""
        doc = AgentDocument.from_domain(agent)
        await doc.save()
        logger.debug(f"保存 Agent {agent.id}")

    async def find_by_id(self, agent_id: str) -> Optional[Agent]:
        """根据 ID 查找 Agent"""
        doc = await AgentDocument.find_one(AgentDocument.agent_id == agent_id)
        return doc.to_domain() if doc else None

    async def find_by_user_id(self, user_id: str) -> Optional[Agent]:
        """根据用户 ID 查找 Agent"""
        doc = await AgentDocument.find_one(AgentDocument.user_id == user_id)
        return doc.to_domain() if doc else None

    async def add_memory(self, agent_id: str, key: str, memory: Memory) -> None:
        """为 Agent 添加记忆"""
        doc = await AgentDocument.find_one(AgentDocument.agent_id == agent_id)
        if not doc:
            raise ValueError(f"Agent {agent_id} 不存在")

        if doc.memories is None:
            doc.memories = {}

        doc.memories[key] = memory.model_dump()
        await doc.save()
        logger.debug(f"为 Agent {agent_id} 添加记忆 {key}")

    async def get_memory(self, agent_id: str, key: str) -> Optional[Memory]:
        """获取 Agent 记忆"""
        doc = await AgentDocument.find_one(AgentDocument.agent_id == agent_id)
        if not doc or not doc.memories:
            return None

        memory_data = doc.memories.get(key)
        if not memory_data:
            return None

        return Memory(**memory_data)

    async def save_memory(self, agent_id: str, key: str, memory: Memory) -> None:
        """保存 Agent 记忆"""
        await self.add_memory(agent_id, key, memory)
