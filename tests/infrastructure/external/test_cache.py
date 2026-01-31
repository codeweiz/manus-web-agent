"""Redis 缓存测试 - 使用真实 Redis 连接

运行前需要启动 Redis:
    docker run -d -p 6379:6379 --name redis redis:latest

运行测试:
    python -m pytest tests/infrastructure/external/test_cache.py -v
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime

# 确保能导入项目代码
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest

from manus_web_agent.infrastructure.external.cache.redis_cache import RedisCache
from manus_web_agent.infrastructure.storage.redis import RedisClient


@pytest.fixture
async def redis_cache():
    """提供 RedisCache 实例"""
    # 先初始化 Redis 客户端 - 使用 get_redis 获取单例并初始化
    from manus_web_agent.infrastructure.storage.redis import get_redis
    redis_client = get_redis()
    await redis_client.initialize()

    cache = RedisCache()
    yield cache

    # 清理
    await redis_client.shutdown()


@pytest.fixture(scope="function")
def test_key():
    """生成唯一的测试键"""
    return f"test:{uuid.uuid4().hex[:8]}:{datetime.now().strftime('%H%M%S')}"


@pytest.mark.asyncio
class TestRedisCache:
    """Redis 缓存功能测试"""

    async def test_set_and_get(self, redis_cache, test_key):
        """测试基本的 set 和 get 操作"""
        test_value = f"test_value_{uuid.uuid4().hex}"

        # 设置值
        result = await redis_cache.set(test_key, test_value)
        assert result is True, "set 应该返回 True"

        # 获取值
        value = await redis_cache.get(test_key)
        assert value == test_value, f"get 应该返回设置值，期望 {test_value}，实际 {value}"

        print(f"✓ Set/Get 测试通过: {test_key} = {test_value}")

    async def test_get_nonexistent_key(self, redis_cache):
        """测试获取不存在的键"""
        nonexistent_key = f"nonexistent:{uuid.uuid4().hex}"
        value = await redis_cache.get(nonexistent_key)
        assert value is None, "获取不存在的键应该返回 None"
        print(f"✓ 非存在键测试通过: {nonexistent_key}")

    async def test_delete(self, redis_cache, test_key):
        """测试删除操作"""
        test_value = "to_be_deleted"

        # 设置值
        await redis_cache.set(test_key, test_value)

        # 确认值存在
        value = await redis_cache.get(test_key)
        assert value == test_value

        # 删除值
        result = await redis_cache.delete(test_key)
        assert result is True, "delete 应该返回 True"

        # 确认值已删除
        value = await redis_cache.get(test_key)
        assert value is None, "删除后应该返回 None"

        print(f"✓ 删除测试通过: {test_key}")

    async def test_exists(self, redis_cache, test_key):
        """测试 exists 操作"""
        # 键不存在
        exists = await redis_cache.exists(test_key)
        assert exists is False, "不存在的键应该返回 False"

        # 设置键
        await redis_cache.set(test_key, "test_value")

        # 键存在
        exists = await redis_cache.exists(test_key)
        assert exists is True, "存在的键应该返回 True"

        print(f"✓ Exists 测试通过: {test_key}")

    async def test_ttl(self, redis_cache, test_key):
        """测试过期时间设置"""
        test_value = "with_ttl"
        expire_seconds = 2

        # 设置带过期时间的值
        await redis_cache.set(test_key, test_value, expire=expire_seconds)

        # 检查 TTL
        ttl = await redis_cache.get_ttl(test_key)
        assert ttl > 0, f"TTL 应该大于 0，实际 {ttl}"
        assert ttl <= expire_seconds, f"TTL 应该小于等于 {expire_seconds}"

        # 等待过期
        await asyncio.sleep(expire_seconds + 1)

        # 确认已过期
        value = await redis_cache.get(test_key)
        assert value is None, "过期后应该返回 None"

        print(f"✓ TTL 测试通过: {test_key} (过期时间 {expire_seconds}s)")

    async def test_keys_pattern(self, redis_cache):
        """测试 keys 模式匹配"""
        prefix = f"pattern_test:{uuid.uuid4().hex[:6]}"

        # 创建多个键
        keys_to_create = [f"{prefix}:key{i}" for i in range(5)]
        for key in keys_to_create:
            await redis_cache.set(key, "value")

        # 使用模式查找
        found_keys = await redis_cache.keys(f"{prefix}:*")
        assert len(found_keys) == 5, f"应该找到 5 个键，实际 {len(found_keys)}"

        # 清理
        for key in keys_to_create:
            await redis_cache.delete(key)

        print(f"✓ Keys 模式测试通过: 找到 {len(found_keys)} 个键")

    async def test_clear_pattern(self, redis_cache):
        """测试 clear_pattern 操作"""
        prefix = f"clear_test:{uuid.uuid4().hex[:6]}"

        # 创建多个键
        keys_to_create = [f"{prefix}:key{i}" for i in range(3)]
        for key in keys_to_create:
            await redis_cache.set(key, "value")

        # 确认键存在
        for key in keys_to_create:
            assert await redis_cache.exists(key) is True

        # 清除匹配模式的键
        deleted_count = await redis_cache.clear_pattern(f"{prefix}:*")
        assert deleted_count == 3, f"应该删除 3 个键，实际 {deleted_count}"

        # 确认键已删除
        for key in keys_to_create:
            assert await redis_cache.exists(key) is False

        print(f"✓ Clear pattern 测试通过: 删除 {deleted_count} 个键")

    async def test_special_characters(self, redis_cache, test_key):
        """测试特殊字符值"""
        special_values = [
            "中文测试",
            "Emoji 🎉🚀",
            "Special chars: !@#$%^&*()",
            "Multi\nLine\nText",
            "Very long text: " + "x" * 10000,
        ]

        for i, value in enumerate(special_values):
            key = f"{test_key}:special{i}"
            await redis_cache.set(key, value)
            retrieved = await redis_cache.get(key)
            assert retrieved == value, f"特殊字符值不匹配: {value[:50]}..."
            await redis_cache.delete(key)

        print(f"✓ 特殊字符测试通过: {len(special_values)} 种类型")


@pytest.mark.asyncio
class TestRedisStorage:
    """Redis 存储连接测试"""

    async def test_connection(self):
        """测试 Redis 连接"""
        storage = RedisClient()

        try:
            await storage.initialize()
            assert storage._client is not None, "客户端应该已初始化"

            # 测试 ping
            result = await storage._client.ping()
            assert result is True, "Ping 应该成功"

            print("✓ Redis 连接测试通过")
        finally:
            await storage.shutdown()

    async def test_pubsub(self):
        """测试发布订阅功能"""
        storage = RedisClient()

        try:
            await storage.initialize()

            # 使用唯一的频道名
            channel = f"test_channel:{uuid.uuid4().hex[:8]}"
            test_message = f"Hello Redis! {uuid.uuid4().hex}"

            # 订阅
            pubsub = storage.client.pubsub()
            await pubsub.subscribe(channel)
            assert pubsub is not None, "订阅应该成功"

            # 等待订阅建立并消费订阅消息
            await asyncio.sleep(0.1)
            await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)

            # 发布消息
            result = await storage.client.publish(channel, test_message)
            assert result >= 0, "发布应该成功"

            # 接收消息 - 使用循环等待消息
            message = None
            for _ in range(50):  # 最多等待5秒
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                if message is not None:
                    break
                await asyncio.sleep(0.1)

            assert message is not None, "应该收到消息"
            assert message["data"] == test_message, f"消息内容不匹配: {message}"

            # 取消订阅
            await pubsub.unsubscribe(channel)
            await pubsub.close()

            print(f"✓ Pub/Sub 测试通过: {channel}")
        finally:
            await storage.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
