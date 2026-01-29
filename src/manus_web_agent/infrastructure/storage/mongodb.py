from functools import lru_cache
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure

from manus_web_agent.core.toml_config import TOML_CONFIG
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB 连接管理器"""

    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._config = TOML_CONFIG.mongodb_config

    async def initialize(self) -> None:
        """初始化 MongoDB 连接"""
        if self._client is not None:
            return

        try:
            # 连接到 MongoDB
            if self._config.username and self._config.password:
                # 使用认证连接
                self._client = AsyncIOMotorClient(
                    self._config.uri,
                    username=self._config.username,
                    password=self._config.password,
                )
            else:
                # 使用无认证连接
                self._client = AsyncIOMotorClient(self._config.uri)

            # 验证连接
            await self._client.admin.command('ping')
            logger.info("成功连接到 MongoDB")
        except ConnectionFailure as e:
            logger.error(f"连接 MongoDB 失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"初始化 MongoDB 失败: {str(e)}")
            raise

    async def shutdown(self) -> None:
        """关闭 MongoDB 连接"""
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.info("断开 MongoDB 连接")
            # 清除缓存
            get_mongodb.cache_clear()

    @property
    def client(self) -> AsyncIOMotorClient:
        """获取已初始化的 MongoDB 客户端"""
        if self._client is None:
            raise RuntimeError("MongoDB 客户端未初始化，请先调用 initialize()")
        return self._client

    @property
    def database(self):
        """获取默认数据库"""
        return self.client[self._config.database]


@lru_cache()
def get_mongodb() -> MongoDB:
    """获取 MongoDB 实例"""
    return MongoDB()
