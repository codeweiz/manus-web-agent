from typing import Protocol, Optional, Any


class Cache(Protocol):
    """缓存服务网关接口"""

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存
        :param key: 键
        :param value: 值
        :param ttl: 过期时间（秒）
        :return: 是否成功
        """
        pass

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存
        :param key: 键
        :return: 值
        """
        pass

    async def delete(self, key: str) -> bool:
        """删除缓存
        :param key: 键
        :return: 是否成功
        """
        pass

    async def exists(self, key: str) -> bool:
        """检查缓存是否存在
        :param key: 键
        :return: 是否存在
        """
        pass

    async def get_ttl(self, key: str) -> Optional[int]:
        """获取缓存过期时间
        :param key: 键
        :return: 过期时间（秒）
        """
        pass

    async def keys(self, pattern: str) -> list[str]:
        """获取所有匹配模式的键
        :param pattern: 模式
        :return: 键列表
        """
        pass

    async def clear_pattern(self, pattern: str) -> int:
        """清除所有匹配模式的键
        :param pattern: 模式
        :return: 清除的键数
        """
        pass
