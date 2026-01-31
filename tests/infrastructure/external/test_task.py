"""Redis Stream Task 测试 - 使用真实 Redis 连接

运行前需要启动 Redis:
    docker run -d -p 6379:6379 --name redis redis:latest

运行测试:
    python -m pytest tests/infrastructure/external/test_task.py -v
"""

import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest

from manus_web_agent.domain.external.task import TaskRunner
from manus_web_agent.infrastructure.external.task.redis_task import RedisStreamTask


class MockTaskRunner(TaskRunner):
    """模拟任务运行器用于测试"""

    def __init__(self):
        self.run_called = False
        self.done_called = False
        self.destroy_called = False
        self.messages = []

    async def run(self, task) -> None:
        """运行任务"""
        self.run_called = True
        # 模拟处理消息
        while not await task.input_stream.is_empty():
            msg_id, msg = await task.input_stream.pop()
            if msg:
                self.messages.append(msg)
                # 发送响应
                await task.output_stream.put(f"Processed: {msg}")

    async def on_done(self, task) -> None:
        """任务完成"""
        self.done_called = True

    async def destroy(self) -> None:
        """销毁"""
        self.destroy_called = True


@pytest.fixture
def mock_runner():
    """提供模拟 TaskRunner"""
    return MockTaskRunner()


@pytest.fixture(autouse=True)
async def init_redis():
    """自动初始化 Redis"""
    from manus_web_agent.infrastructure.storage.redis import get_redis
    redis_client = get_redis()
    await redis_client.initialize()
    yield
    await redis_client.shutdown()


@pytest.mark.asyncio
class TestRedisStreamTask:
    """Redis Stream 任务测试"""

    async def test_create_task(self, mock_runner):
        """测试创建任务"""
        task = RedisStreamTask.create(mock_runner)

        assert task is not None, "应该创建任务"
        assert task.id is not None, "任务应该有 ID"
        assert task.id.startswith("task_"), "任务 ID 应该以 task_ 开头"
        assert task.input_stream is not None, "应该有输入流"
        assert task.output_stream is not None, "应该有输出流"
        assert not task.done, "任务初始状态应该是未完成"

        print(f"  任务 ID: {task.id}")
        print(f"✓ 创建任务测试通过")

        # 清理
        task.cancel()

    async def test_get_task(self, mock_runner):
        """测试获取任务"""
        task = RedisStreamTask.create(mock_runner)

        # 通过 ID 获取任务
        retrieved_task = RedisStreamTask.get(task.id)
        assert retrieved_task is not None, "应该能获取到任务"
        assert retrieved_task.id == task.id, "任务 ID 应该匹配"

        print(f"✓ 获取任务测试通过")

        # 清理
        task.cancel()

    async def test_run_task(self, mock_runner):
        """测试运行任务"""
        task = RedisStreamTask.create(mock_runner)

        # 添加测试消息
        test_msg = f"Test message: {uuid.uuid4().hex}"
        await task.input_stream.put(test_msg)

        # 运行任务
        await task.run()

        # 等待任务处理
        await asyncio.sleep(0.5)

        assert mock_runner.run_called, "run 应该被调用"

        print(f"✓ 运行任务测试通过")

        # 清理
        task.cancel()

    async def test_task_io_streams(self, mock_runner):
        """测试任务输入输出流"""
        task = RedisStreamTask.create(mock_runner)

        # 发送多条消息
        messages = [f"Message {i}: {uuid.uuid4().hex}" for i in range(3)]
        for msg in messages:
            await task.input_stream.put(msg)

        # 验证输入流大小
        size = await task.input_stream.size()
        assert size >= 3, f"输入流应该有至少 3 条消息，实际 {size}"

        # 运行任务
        await task.run()
        await asyncio.sleep(0.5)

        # 检查输出
        responses = []
        for _ in range(5):  # 尝试读取最多 5 条
            msg_id, msg = await task.output_stream.get(block_ms=200)
            if msg:
                responses.append(msg)

        print(f"  收到 {len(responses)} 个响应")
        print(f"✓ 任务 IO 流测试通过")

        # 清理
        task.cancel()

    async def test_cancel_task(self, mock_runner):
        """测试取消任务"""
        task = RedisStreamTask.create(mock_runner)

        # 运行任务
        await task.run()

        # 取消任务
        result = task.cancel()
        assert result is True, "取消应该返回 True"

        # 等待取消生效
        await asyncio.sleep(0.2)

        print(f"✓ 取消任务测试通过")

    async def test_multiple_tasks(self):
        """测试多个任务并存"""
        runners = [MockTaskRunner() for _ in range(3)]
        tasks = [RedisStreamTask.create(r) for r in runners]

        # 验证所有任务都有唯一 ID
        task_ids = [t.id for t in tasks]
        assert len(set(task_ids)) == 3, "每个任务应该有唯一的 ID"

        # 向每个任务发送消息
        for i, task in enumerate(tasks):
            await task.input_stream.put(f"Message for task {i}")
            await task.run()

        await asyncio.sleep(0.5)

        # 验证每个 runner 都被调用
        for runner in runners:
            assert runner.run_called, "每个 runner 应该被调用"

        print(f"  创建了 {len(tasks)} 个任务")
        print(f"✓ 多任务测试通过")

        # 清理
        for task in tasks:
            task.cancel()

    async def test_destroy_all_tasks(self):
        """测试销毁所有任务"""
        runners = [MockTaskRunner() for _ in range(2)]
        tasks = [RedisStreamTask.create(r) for r in runners]

        # 运行任务
        for task in tasks:
            await task.run()

        await asyncio.sleep(0.2)

        # 销毁所有任务
        await RedisStreamTask.destroy()

        # 验证所有 runner 的 destroy 被调用
        for runner in runners:
            assert runner.destroy_called, "每个 runner 的 destroy 应该被调用"

        print(f"✓ 销毁所有任务测试通过")


@pytest.mark.asyncio
class TestRedisStreamTaskEdgeCases:
    """边界情况测试"""

    async def test_get_nonexistent_task(self):
        """测试获取不存在的任务"""
        task = RedisStreamTask.get("nonexistent_task_id")
        assert task is None, "不存在的任务应该返回 None"
        print(f"✓ 获取不存在任务测试通过")

    async def test_cancel_not_running_task(self, mock_runner):
        """测试取消未运行的任务"""
        task = RedisStreamTask.create(mock_runner)

        # 任务未运行，取消应该返回 False
        result = task.cancel()
        assert result is False, "取消未运行的任务应该返回 False"

        print(f"✓ 取消未运行任务测试通过")

    async def test_task_done_property(self, mock_runner):
        """测试任务 done 属性"""
        task = RedisStreamTask.create(mock_runner)

        # 初始状态
        assert not task.done, "新任务应该未完成"

        # 运行并取消
        await task.run()
        task.cancel()
        await asyncio.sleep(0.2)

        print(f"✓ Done 属性测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
