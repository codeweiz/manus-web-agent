from enum import Enum
from typing import Optional, List, Dict

from pydantic import BaseModel, Field, field_validator


class MCPTransport(str, Enum):
    """MCP 传输协议"""

    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"


class MCPServerConfig(BaseModel):
    """MCP 服务端配置"""

    # STDIO 使用
    command: Optional[str] = Field(default=None, description="命令")
    args: Optional[List[str]] = Field(default=None, description="参数")

    # SSE、Streamable HTTP 使用
    url: Optional[str] = Field(default=None, description="URL")
    headers: Optional[Dict[str, str]] = Field(default=None, description="头信息")

    # 通用属性
    transport: MCPTransport = Field(..., description="传输协议")
    enabled: bool = Field(default=True, description="是否启用")
    description: Optional[str] = Field(default=None, description="描述")
    env: Optional[Dict[str, str]] = Field(default=None, description="环境变量")

    @field_validator("url")
    @classmethod
    def validate_url_for_http_transport(cls, v: Optional[str], values) -> Optional[str]:
        """验证 URL 在 HTTP 传输协议下是否合法"""
        if hasattr(values, "data"):
            transport = values.data.get("transport")
            if transport in [MCPTransport.SSE, MCPTransport.STREAMABLE_HTTP] and v is None:
                raise ValueError(f"URL is required for {transport} transport")
        return v

    @field_validator("command")
    @classmethod
    def validate_command_for_stdio(cls, v: Optional[str], values) -> Optional[str]:
        """验证命令在 STDIO 传输协议下是否合法"""
        if hasattr(values, "data"):
            transport = values.data.get("transport")
            if transport == MCPTransport.STDIO and v is None:
                raise ValueError(f"Command is required for {transport} transport")
        return v

    class Config:
        extra = "allow"


class MCPConfig(BaseModel):
    """MCP 配置"""

    mcpServers: Dict[str, MCPServerConfig] = Field(default_factory=dict, description="MCP 服务端配置")

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"
