"""Redis 流消息队列实现"""

import asyncio
import logging
from typing import Optional, Tuple

from manus_web_agent.domain.external.message_queue import MessageQueue
from manus_web_agent.infrastructure.storage.redis import get_redis

logger = logging.getLogger(__name__)


class RedisStreamQueue(MessageQueue):
    """Redis 流消息队列实现"""

    def __init__(self, stream_key: str):
        self._stream_key = stream_key
        self._redis = get_redis()
        self._last_id = "0"

    async def put(self, message: str) -> str:
        """添加消息到队列

        :param message: 消息内容
        :return: 消息 ID
        """
        client = self._redis.client
        result = await client.xadd(self._stream_key, {"data": message})
        return result

    async def get(
        self, start_id: Optional[str] = None, block_ms: int = 5000
    ) -> Tuple[Optional[str], Optional[str]]:
        """从队列获取消息

        :param start_id: 起始 ID
        :param block_ms: 阻塞等待时间（毫秒）
        :return: (消息 ID, 消息内容)
        """
        client = self._redis.client
        last_id = start_id or self._last_id

        try:
            result = await client.xread(
                {self._stream_key: last_id}, block=block_ms
            )

            if not result:
                return None, None

            # 解析结果
            stream_name, messages = result[0]
            if not messages:
                return None, None

            msg_id, msg_data = messages[0]
            self._last_id = msg_id

            return msg_id, msg_data.get("data")

        except Exception as e:
            logger.error(f"Redis 流读取错误: {e}")
            return None, None

    async def pop(self) -> Tuple[Optional[str], Optional[str]]:
        """弹出队列中的消息（非阻塞）"""
        return await self.get(block_ms=0)

    async def is_empty(self) -> bool:
        """检查队列是否为空"""
        client = self._redis.client
        length = await client.xlen(self._stream_key)
        return length == 0

    async def size(self) -> int:
        """获取队列长度"""
        client = self._redis.client
        return await client.xlen(self._stream_key)

    async def clear(self) -> None:
        """清空队列"""
        client = self._redis.client
        await client.delete(self._stream_key)
        self._last_id = "0"
