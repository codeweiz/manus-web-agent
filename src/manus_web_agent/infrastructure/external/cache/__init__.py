"""缓存模块"""

from manus_web_agent.infrastructure.external.cache.redis_cache import RedisCache


def get_cache():
    """获取缓存实例"""
    return RedisCache()


__all__ = ["RedisCache", "get_cache"]
