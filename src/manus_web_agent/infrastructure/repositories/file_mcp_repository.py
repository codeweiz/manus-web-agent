"""File MCP Repository 实现"""

import json
import logging
from typing import Dict, Any

from manus_web_agent.core.toml_config import TOML_CONFIG
from manus_web_agent.domain.repositories.mcp_repository import MCPRepository

logger = logging.getLogger(__name__)


class FileMCPRepository(MCPRepository):
    """从文件读取 MCP 配置的仓库"""

    def __init__(self):
        self._config_path = TOML_CONFIG.mcp_config.config_path
        self._cache: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """从文件加载配置"""
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._cache = json.load(f)
            logger.info(f"从 {self._config_path} 加载 MCP 配置")
        except FileNotFoundError:
            logger.warning(f"MCP 配置文件不存在: {self._config_path}")
            self._cache = {}
        except json.JSONDecodeError as e:
            logger.error(f"MCP 配置文件格式错误: {e}")
            self._cache = {}

    async def get_mcp_config(self) -> Dict[str, Any]:
        """获取 MCP 配置"""
        return self._cache

    async def reload_config(self) -> None:
        """重新加载配置"""
        self._load_config()
