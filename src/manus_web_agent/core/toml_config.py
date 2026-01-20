import os
from typing import Optional

from pydantic import BaseModel, Field


class LlmConfig(BaseModel):
    """大语言模型配置"""

    provider: str = Field(default="deepseek", description="提供者")

    model: str = Field(default="deepseek-chat", description="模型名")

    api_key: str = Field(default="", description="API KEY")

    base_url: str = Field(default="https://api.deepseek.com", description="URL 前缀")

    temperature: float = Field(default=0.7, description="温度")

    max_tokens: int = Field(default=1024, description="最大 token 数")


class MongodbConfig(BaseModel):
    """MongoDB 配置"""

    uri: str = Field(default="mongodb://localhost:27017", description="URI")

    database: str = Field(default="manus_web_agent", description="数据库名")

    username: Optional[str] = Field(default=None, description="用户名")

    password: Optional[str] = Field(default=None, description="密码")


class RedisConfig(BaseModel):
    """Redis 配置"""

    host: str = Field(default="localhost", description="主机名")

    port: int = Field(default=6379, description="端口")

    db: int = Field(default=0, description="数据库名")

    password: Optional[str] = Field(default=None, description="密码")


class SandboxConfig(BaseModel):
    """沙箱配置"""

    address: Optional[str] = Field(default=None, description="地址")

    image: Optional[str] = Field(default=None, description="镜像")

    name_prefix: Optional[str] = Field(default=None, description="容器名前缀")

    ttl_minutes: Optional[int] = Field(default=30, description="容器存活时间（分钟）")

    network: Optional[str] = Field(default=None, description="网络")

    chrome_args: Optional[str] = Field(default=None, description="Chromium 参数")

    https_proxy: Optional[str] = Field(default=None, description="HTTPS 代理")

    http_proxy: Optional[str] = Field(default=None, description="HTTP 代理")

    no_proxy: Optional[str] = Field(default=None, description="不代理")


class SearchConfig(BaseModel):
    """搜索引擎配置"""

    provider: str = Field(default="bing", description="提供者：baidu、google、bing")

    api_key: Optional[str] = Field(default=None, description="API KEY")

    engine_id: Optional[str] = Field(default=None, description="引擎 ID")


class McpConfig(BaseModel):
    """MCP 配置"""

    config_path: str = Field(default="/etc/mcp.json", description="MCP 配置文件地址")


class LangSmithConfig(BaseModel):
    """LangSmith 追踪配置"""

    tracing: bool = Field(default=False, description="是否启用追踪")

    api_key: str = Field(default="", description="API KEY")


class TomlConfig(BaseModel):
    """Toml 配置"""

    llm_config: LlmConfig = Field(default_factory=LlmConfig, description="大语言模型配置")

    mongodb_config: MongodbConfig = Field(default_factory=MongodbConfig, description="MongoDB 配置")

    redis_config: RedisConfig = Field(default_factory=RedisConfig, description="Redis 配置")

    sandbox_config: SandboxConfig = Field(default_factory=SandboxConfig, description="沙箱配置")

    search_config: SearchConfig = Field(default_factory=SearchConfig, description="搜索引擎配置")

    mcp_config: McpConfig = Field(default_factory=McpConfig, description="MCP 配置")

    langsmith_config: LangSmithConfig = Field(default_factory=LangSmithConfig, description="LangSmith 追踪配置")


def load_toml_config(file_path: str = "../../.config.toml") -> TomlConfig:
    """加载 .config.toml 的配置"""

    import tomllib
    from pathlib import Path

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError

    try:
        with open(str(path), "rb") as f:
            toml_data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise e

    return TomlConfig(
        llm_config=LlmConfig(**toml_data.get("llm") if toml_data.get("llm") else {}),
        mongodb_config=MongodbConfig(**toml_data.get("mongodb") if toml_data.get("mongodb") else {}),
        redis_config=RedisConfig(**toml_data.get("redis") if toml_data.get("redis") else {}),
        sandbox_config=SandboxConfig(**toml_data.get("sandbox") if toml_data.get("sandbox") else {}),
        search_config=SearchConfig(**toml_data.get("search") if toml_data.get("search") else {}),
        mcp_config=McpConfig(**toml_data.get("mcp") if toml_data.get("mcp") else {}),
        langsmith_config=LangSmithConfig(**toml_data.get("langsmith") if toml_data.get("langsmith") else {}),
    )


TOML_CONFIG = load_toml_config()

if TOML_CONFIG.langsmith_config.tracing:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = TOML_CONFIG.langsmith_config.api_key


def get_config():
    """获取全局配置"""
    if TOML_CONFIG is None:
        return load_toml_config()
    return TOML_CONFIG
