from typing import Protocol, Optional

from manus_web_agent.domain.models.agent import Agent
from manus_web_agent.domain.models.memory import Memory


class AgentRepository(Protocol):
    """Agent Repository"""

    async def save(self, agent: Agent) -> None:
        """保存或更新 Agent"""
        pass

    async def find_by_id(self, agent_id: str) -> Optional[Agent]:
        """根据 ID 查找 Agent"""
        pass

    async def add_memory(self, agent_id: str, name: str, memory: Memory) -> None:
        """为 Agent 添加记忆"""
        pass

    async def get_memory(self, agent_id: str, name: str) -> Memory:
        """获取 Agent 的记忆"""
        pass

    async def save_memory(self, agent_id: str, name: str, memory: Memory) -> None:
        """更新 Agent 的记忆"""
        pass
