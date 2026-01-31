"""Redis 缓存实现"""

import logging
from typing import List, Optional

from manus_web_agent.domain.external.cache import Cache
from manus_web_agent.infrastructure.storage.redis import get_redis

logger = logging.getLogger(__name__)


class RedisCache(Cache):
    """Redis 缓存实现"""

    def __init__(self):
        self._redis = get_redis()

    async def get(self, key: str) -> Optional[str]:
        """获取缓存值"""
        try:
            client = self._redis.client
            value = await client.get(key)
            return value
        except Exception as e:
            logger.error(f"Redis get 错误: {e}")
            return None

    async def set(self, key: str, value: str, expire: int = 3600) -> bool:
        """设置缓存值"""
        try:
            client = self._redis.client
            await client.set(key, value, ex=expire)
            return True
        except Exception as e:
            logger.error(f"Redis set 错误: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            client = self._redis.client
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete 错误: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            client = self._redis.client
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists 错误: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """获取键的剩余过期时间（秒）"""
        try:
            client = self._redis.client
            ttl = await client.ttl(key)
            return ttl
        except Exception as e:
            logger.error(f"Redis ttl 错误: {e}")
            return -1

    async def keys(self, pattern: str) -> List[str]:
        """根据模式查找键"""
        try:
            client = self._redis.client
            keys = await client.keys(pattern)
            return keys
        except Exception as e:
            logger.error(f"Redis keys 错误: {e}")
            return []

    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的所有键"""
        try:
            client = self._redis.client
            keys = await client.keys(pattern)
            if keys:
                await client.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.error(f"Redis clear_pattern 错误: {e}")
            return 0
