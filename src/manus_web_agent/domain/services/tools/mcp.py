import logging
import os
from contextlib import AsyncExitStack
from typing import Optional, Dict, List, Any

from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Tool

from manus_web_agent.domain.models.mcp_config import MCPConfig, MCPServerConfig, MCPTransport
from manus_web_agent.domain.models.tool_result import ToolResult

logger = logging.getLogger(__name__)


class MCPClientManager:
    """MCP 客户端管理器"""

    def __init__(self, config: Optional[MCPConfig] = None):
        self._clients: Dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()
        self._tools_cache: Dict[str, List[Tool]] = {}
        self._initialized = False
        self._config = config

    async def initialize(self):
        """初始化 MCP 客户端管理器"""
        if self._initialized:
            return

        try:
            logger.info(f"从配置加载了 {len(self._config.mcpServers)} 个 MCP 服务器配置")

            await self._connect_servers()
            self._initialized = True
            logger.info(f"连接到 {len(self._clients)} 个 MCP 服务器")
        except Exception as e:
            logger.error(f"初始化 MCP 客户端管理器失败: {e}")
            raise e

    async def _connect_servers(self):
        """连接所有可用的 MCP 服务器"""

        for server_name, server_config in self._config.mcpServers.items():
            if not server_config.enabled:
                continue

            try:
                await self._connect_server(server_name, server_config)
            except Exception as e:
                logger.error(f"连接 MCP 服务器失败: {server_name} - {e}")
                continue

    async def _connect_server(self, server_name: str, server_config: MCPServerConfig):
        """连接单个 MCP 服务器"""

        try:
            transport_type = server_config.transport

            if transport_type == MCPTransport.STDIO:
                await self._connect_stdio_server(server_name, server_config)
            elif transport_type == MCPTransport.SSE:
                await self._connect_http_server(server_name, server_config)
            elif transport_type == MCPTransport.STREAMABLE_HTTP:
                await self._connect_streamable_http_server(server_name, server_config)
            else:
                raise ValueError(f"Unsupported transport type: {transport_type}")
        except Exception as e:
            logger.error(f"连接 MCP 服务器失败: {server_name} - {e}")
            raise e

    async def _connect_stdio_server(self, server_name: str, server_config: MCPServerConfig):
        """连接 STDIO 服务器"""

        command = server_config.command
        args = server_config.args or []
        env = server_config.env or {}
        logger.info(f"连接 STDIO 服务器: {server_name} - {command} {args} {env}")

        if not command:
            raise ValueError(f"Command is required for STDIO transport")

        # 创建服务器参数
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env={**os.environ, **env},
        )

        try:
            # 建立连接
            stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
            read_stream, write_stream = stdio_transport

            # 创建会话
            session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))

            # 初始化会话
            await session.initialize()

            # 缓存客户端
            self._clients[server_name] = session

            # 获取并缓存工具列表
            await self._cache_server_tools(server_name, session)
            logger.info(f"连接 STDIO 服务器成功: {server_name}")
        except Exception as e:
            logger.error(f"连接 STDIO 服务器失败: {server_name} - {e}")
            raise e

    async def _connect_http_server(self, server_name: str, server_config: MCPServerConfig):
        """连接 HTTP 服务器"""
        url = server_config.url
        if not url:
            raise ValueError(f"URL is required for HTTP transport")

        try:
            # 建立 SSE 连接
            sse_transport = await self._exit_stack.enter_async_context(sse_client(url))
            read_stream, write_stream = sse_transport

            # 创建会话
            session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))

            # 初始化会话
            await session.initialize()

            # 缓存客户端
            self._clients[server_name] = session

            # 获取并缓存工具列表
            await self._cache_server_tools(server_name, session)
            logger.info(f"连接 HTTP 服务器成功: {server_name}")
        except Exception as e:
            logger.error(f"连接 HTTP 服务器失败: {server_name} - {e}")
            raise e

    async def _connect_streamable_http_server(self, server_name: str, server_config: MCPServerConfig):
        """连接 Streamable HTTP 服务器
        :param server_name: 服务器名称
        :param server_config: 服务器配置
        :return: 会话
        """
        url = server_config.url
        if not url:
            raise ValueError(f"URL is required for Streamable HTTP transport")

        # 获取可选配置
        headers = server_config.headers or {}

        try:
            # 准备连接参数
            client_params = {"url": url}

            # 添加自定义 headers
            if headers:
                client_params["headers"] = headers

            # 建立 streamable-http 连接
            streamable_transport = await self._exit_stack.enter_async_context(
                streamable_http_client(**client_params)
            )

            # 解包返回的流和可选的第三个参数
            if len(streamable_transport) == 3:
                read_stream, write_stream, _ = streamable_transport
            else:
                read_stream, write_stream = streamable_transport

            # 创建 MCP 会话
            session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))

            # 初始化会话
            await session.initialize()

            # 缓存客户端
            self._clients[server_name] = session

            # 获取并缓存工具列表
            await self._cache_server_tools(server_name, session)
            logger.info(f"连接 Streamable HTTP 服务器成功: {server_name}")
        except Exception as e:
            logger.error(f"连接 Streamable HTTP 服务器失败: {server_name} - {e}")
            raise e

    async def _cache_server_tools(self, server_name: str, session: ClientSession):
        """缓存服务器工具列表"""
        try:
            tools_response = await session.list_tools()
            tools = tools_response.tools if tools_response else []
            self._tools_cache[server_name] = tools
            logger.info(f"缓存服务器工具列表成功: {server_name} - {len(tools)} 个工具")
        except Exception as e:
            logger.error(f"缓存服务器工具列表失败: {server_name} - {e}")
            raise e

    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """获取所有 MCP 工具列表"""
        all_tools = []

        for server_name, tools in self._tools_cache.items():
            for tool in tools:
                if server_name.startswith('mcp_'):
                    tool_name = f"{server_name}_{tool.name}"
                else:
                    tool_name = f"mcp_{server_name}_{tool.name}"

                tool_schema = {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": f"[{server_name}] {tool.description or tool.name}",
                        "parameters": tool.inputSchema,
                    }
                }
                all_tools.append(tool_schema)
        return all_tools

    async def call_tool(self, tool_name: str, args: Dict[str, Any]):
        """调用工具"""
        try:
            # 解析工具
            server_name = None
            original_tool_name = None

            # 查找匹配的服务器名称
            for svr_name in self._config.mcpServers.keys():
                expected_prefix = svr_name if svr_name.startswith('mcp_') else f"mcp_{svr_name}"
                if tool_name.startswith(f"{expected_prefix}_"):
                    server_name = svr_name
                    original_tool_name = tool_name[len(expected_prefix) + 1:]
                    break

            if not server_name or not original_tool_name:
                raise ValueError(f"Tool '{tool_name}' not found")

            # 获取客户端会话
            session = self._clients.get(server_name)
            if not session:
                return ToolResult(success=False, message=f"Server '{server_name}' not connected")

            # 调用工具
            result = await session.call_tool(original_tool_name, args)

            # 处理结果
            if result:
                content = []
                if hasattr(result, "content") and result.content:
                    for item in result.content:
                        if hasattr(item, "text"):
                            content.append(item.text)
                        else:
                            content.append(str(item))
                return ToolResult(success=True, data="\n".join(content) if content else "工具执行成功")
            else:
                return ToolResult(success=True, data="工具执行成功")
        except Exception as e:
            logger.error(f"调用工具失败: {tool_name} - {e}")
            return ToolResult(success=False, message=f"调用工具失败: {str(e)}")

    async def cleanup(self):
        """清理 MCP 客户端管理器"""
        try:
            await self._exit_stack.aclose()
            self._clients.clear()
            self._tools_cache.clear()
            self._initialized = False
            logger.info("MCP 客户端管理器已清理")
        except Exception as e:
            logger.error(f"清理 MCP 客户端管理器失败: {e}")
            raise e
