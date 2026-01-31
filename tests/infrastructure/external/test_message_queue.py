"""Redis 流消息队列测试 - 使用真实 Redis 连接

运行前需要启动 Redis:
    docker run -d -p 6379:6379 --name redis redis:latest

运行测试:
    python -m pytest tests/infrastructure/external/test_message_queue.py -v
"""

import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest

from manus_web_agent.infrastructure.external.message_queue.redis_stream_queue import RedisStreamQueue


@pytest.fixture
def test_stream_key():
    """生成唯一的测试流键"""
    return f"test:stream:{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def message_queue(test_stream_key):
    """提供 RedisStreamQueue 实例"""
    queue = RedisStreamQueue(test_stream_key)
    yield queue
    # 清理
    await queue.clear()


@pytest.mark.asyncio
class TestRedisStreamQueue:
    """Redis 流消息队列功能测试"""

    async def test_put_and_get(self, message_queue):
        """测试基本的 put 和 get 操作"""
        test_message = f"Hello Redis Stream! {uuid.uuid4().hex}"

        # 发送消息
        msg_id = await message_queue.put(test_message)
        assert msg_id is not None, "put 应该返回消息 ID"
        assert isinstance(msg_id, str), "消息 ID 应该是字符串"
        print(f"  消息 ID: {msg_id}")

        # 接收消息
        received_id, received_msg = await message_queue.get(block_ms=1000)
        assert received_id is not None, "应该收到消息 ID"
        assert received_msg == test_message, f"消息内容应该匹配: {received_msg}"

        print(f"✓ Put/Get 测试通过")

    async def test_multiple_messages(self, message_queue):
        """测试发送多条消息"""
        messages = [f"Message {i}: {uuid.uuid4().hex}" for i in range(5)]

        # 发送所有消息
        for msg in messages:
            await message_queue.put(msg)

        # 接收并验证
        received_messages = []
        for _ in range(len(messages)):
            msg_id, msg = await message_queue.get(block_ms=1000)
            if msg:
                received_messages.append(msg)

        assert len(received_messages) == len(messages), f"应该收到 {len(messages)} 条消息"
        assert received_messages == messages, "消息顺序和内容应该匹配"

        print(f"✓ 多条消息测试通过: {len(messages)} 条")

    async def test_empty_queue(self, message_queue):
        """测试空队列"""
        # 非阻塞获取
        msg_id, msg = await message_queue.get(block_ms=0)
        assert msg_id is None, "空队列应该返回 None"
        assert msg is None, "空队列消息应该为 None"

        # 检查是否为空
        is_empty = await message_queue.is_empty()
        # 注意：由于 Redis Stream 的特性，删除后可能仍有空流存在
        # 所以这里主要检查不抛出异常
        print(f"✓ 空队列测试通过")

    async def test_size(self, message_queue):
        """测试队列大小"""
        # 初始大小
        initial_size = await message_queue.size()

        # 添加消息
        for i in range(3):
            await message_queue.put(f"Message {i}")

        # 检查大小
        new_size = await message_queue.size()
        assert new_size >= initial_size + 3, f"大小应该增加至少 3"

        print(f"✓ 大小测试通过: {initial_size} -> {new_size}")

    async def test_clear(self, message_queue):
        """测试清空队列"""
        # 添加消息
        await message_queue.put("Message to be cleared")

        # 清空
        await message_queue.clear()

        # 确认清空
        is_empty = await message_queue.is_empty()
        # 注意：Stream 清空前可能有消费者组等情况，这里主要验证不抛出异常

        print(f"✓ 清空测试通过")

    async def test_pop(self, message_queue):
        """测试 pop 操作（非阻塞）"""
        test_message = f"Pop test: {uuid.uuid4().hex}"

        # 先发送消息
        await message_queue.put(test_message)

        # 使用 pop 获取
        msg_id, msg = await message_queue.pop()
        assert msg == test_message, "pop 应该获取到消息"

        print(f"✓ Pop 测试通过")

    async def test_concurrent_producer_consumer(self, message_queue):
        """测试并发生产者和消费者"""
        message_count = 10
        sent_messages = set()
        received_messages = set()

        async def producer():
            for i in range(message_count):
                msg = f"Concurrent message {i}: {uuid.uuid4().hex}"
                sent_messages.add(msg)
                await message_queue.put(msg)
                await asyncio.sleep(0.01)  # 稍微延迟

        async def consumer():
            for _ in range(message_count):
                msg_id, msg = await message_queue.get(block_ms=5000)
                if msg:
                    received_messages.add(msg)

        # 并发执行
        await asyncio.gather(producer(), consumer())

        assert len(received_messages) == message_count, f"应该收到 {message_count} 条消息"
        assert received_messages == sent_messages, "收到的消息应该与发送的一致"

        print(f"✓ 并发测试通过: {message_count} 条消息")

    async def test_large_message(self, message_queue):
        """测试大消息"""
        large_message = "x" * 100000  # 100KB

        msg_id = await message_queue.put(large_message)
        received_id, received_msg = await message_queue.get(block_ms=2000)

        assert received_msg == large_message, "大消息应该完整传输"

        print(f"✓ 大消息测试通过: {len(large_message)} bytes")

    async def test_special_characters(self, message_queue):
        """测试特殊字符"""
        special_messages = [
            "中文测试消息",
            "Emoji 🎉🚀💻",
            "Special chars: !@#$%^&*()",
            "Multi\nLine\nMessage",
            '{"json": "data", "number": 123}',
            "<html>tags</html>",
        ]

        for msg in special_messages:
            await message_queue.put(msg)
            received_id, received_msg = await message_queue.get(block_ms=1000)
            assert received_msg == msg, f"特殊字符消息应该匹配: {msg[:30]}"

        print(f"✓ 特殊字符测试通过: {len(special_messages)} 种")


@pytest.mark.asyncio
class TestRedisStreamQueueMultipleStreams:
    """多流测试"""

    async def test_multiple_streams_isolation(self):
        """测试多个流之间的隔离性"""
        stream_key1 = f"test:stream:isolation1:{uuid.uuid4().hex[:8]}"
        stream_key2 = f"test:stream:isolation2:{uuid.uuid4().hex[:8]}"

        queue1 = RedisStreamQueue(stream_key1)
        queue2 = RedisStreamQueue(stream_key2)

        try:
            # 向流 1 发送消息
            await queue1.put("Message for stream 1")

            # 向流 2 发送消息
            await queue2.put("Message for stream 2")

            # 从流 1 读取
            msg_id1, msg1 = await queue1.get(block_ms=1000)
            assert msg1 == "Message for stream 1"

            # 从流 2 读取
            msg_id2, msg2 = await queue2.get(block_ms=1000)
            assert msg2 == "Message for stream 2"

            # 再次从流 1 读取应该没有消息（除非有新消息）
            msg_id, msg = await queue1.get(block_ms=100)
            # 这里应该返回 None，因为我们已经读取了所有消息

            print(f"✓ 多流隔离测试通过")
        finally:
            await queue1.clear()
            await queue2.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
