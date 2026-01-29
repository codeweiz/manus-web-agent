from functools import lru_cache
from typing import Optional

from redis.asyncio import Redis

from manus_web_agent.core.toml_config import TOML_CONFIG
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 连接管理器"""

    def __init__(self):
        self._client: Optional[Redis] = None
        self._config = TOML_CONFIG.redis_config

    async def initialize(self) -> None:
        """初始化 Redis 连接"""
        if self._client is not None:
            return

        try:
            # 连接到 Redis
            self._client = Redis(
                host=self._config.host,
                port=self._config.port,
                db=self._config.db,
                password=self._config.password,
                decode_responses=True
            )
            # 验证连接
            await self._client.ping()
            logger.info("成功连接到 Redis")
        except Exception as e:
            logger.error(f"连接 Redis 失败: {str(e)}")
            raise

    async def shutdown(self) -> None:
        """关闭 Redis 连接"""
        if self._client is not None:
            await self._client.close()
            self._client = None
            logger.info("断开 Redis 连接")
            # 清除缓存
            get_redis.cache_clear()

    @property
    def client(self) -> Redis:
        """获取已初始化的 Redis 客户端"""
        if self._client is None:
            raise RuntimeError("Redis 客户端未初始化，请先调用 initialize()")
        return self._client


@lru_cache()
def get_redis() -> RedisClient:
    """获取 Redis 客户端实例"""
    return RedisClient()
