from typing import Protocol, Any, Optional, Tuple


class MessageQueue(Protocol):
    """消息队列服务网关接口"""

    async def put(self, message: Any) -> str:
        """发布消息
        :param message: 消息
        :return: 消息 ID
        """
        pass

    async def get(self, start_id: Optional[str] = None, block_ms: Optional[int] = None) -> Tuple[str, Any]:
        """订阅频道
        :param start_id: 起始 ID
        :param block_ms: 阻塞时间（毫秒）
        :return: 消息 ID 和消息
        """
        pass

    async def pop(self) -> Tuple[str, Any]:
        """弹出消息
        :return: 消息 ID 和消息
        """
        pass

    async def clear(self) -> None:
        """清空队列"""
        pass

    async def is_empty(self) -> bool:
        """检查队列是否为空
        :return: 是否为空
        """
        pass

    async def size(self) -> int:
        """获取队列大小
        :return: 队列大小
        """
        pass

    async def delete_message(self, message_id: str) -> bool:
        """删除消息
        :param message_id: 消息 ID
        :return: 是否成功
        """
        pass
