from typing import Protocol

from manus_web_agent.domain.models.mcp_config import MCPConfig


class MCPRepository(Protocol):
    """MCP Repository"""

    async def get_mcp_config(self) -> MCPConfig:
        """获取 MCP 配置"""
        pass
