"""Redis 流任务实现"""

import asyncio
import logging
import uuid
from typing import Dict, Optional

from manus_web_agent.domain.external.task import Task, TaskRunner
from manus_web_agent.infrastructure.external.message_queue.redis_stream_queue import (
    RedisStreamQueue,
)

logger = logging.getLogger(__name__)


class RedisStreamTask(Task):
    """Redis 流任务实现"""

    _registry: Dict[str, "RedisStreamTask"] = {}

    def __init__(
        self,
        task_id: str,
        runner: TaskRunner,
        input_stream: RedisStreamQueue,
        output_stream: RedisStreamQueue,
    ):
        self._id = task_id
        self._runner = runner
        self._input_stream = input_stream
        self._output_stream = output_stream
        self._done = False
        self._cancelled = False
        self._task: Optional[asyncio.Task] = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def input_stream(self) -> RedisStreamQueue:
        return self._input_stream

    @property
    def output_stream(self) -> RedisStreamQueue:
        return self._output_stream

    @property
    def done(self) -> bool:
        return self._done

    @classmethod
    def create(cls, runner: TaskRunner) -> "RedisStreamTask":
        """创建新任务"""
        task_id = f"task_{uuid.uuid4().hex[:16]}"

        # 创建输入输出流
        input_stream = RedisStreamQueue(f"task:{task_id}:input")
        output_stream = RedisStreamQueue(f"task:{task_id}:output")

        task = cls(task_id, runner, input_stream, output_stream)
        cls._registry[task_id] = task

        logger.info(f"创建 Redis 流任务 {task_id}")
        return task

    @classmethod
    def get(cls, task_id: str) -> Optional["RedisStreamTask"]:
        """获取任务"""
        return cls._registry.get(task_id)

    async def run(self) -> None:
        """运行任务"""
        if self._task and not self._task.done():
            return

        self._task = asyncio.create_task(self._run_task())

    async def _run_task(self) -> None:
        """内部运行方法"""
        try:
            await self._runner.run(self)
        except asyncio.CancelledError:
            logger.info(f"任务 {self._id} 被取消")
            self._cancelled = True
        except Exception as e:
            logger.exception(f"任务 {self._id} 运行错误: {e}")
        finally:
            self._done = True
            try:
                await self._runner.on_done(self)
            except Exception as e:
                logger.error(f"任务 {self._id} on_done 错误: {e}")

    def cancel(self) -> bool:
        """取消任务"""
        if self._task and not self._task.done():
            self._task.cancel()
            self._cancelled = True
            return True
        return False

    @classmethod
    async def destroy(cls) -> None:
        """销毁所有任务"""
        for task in list(cls._registry.values()):
            task.cancel()
            if task._runner:
                try:
                    await task._runner.destroy()
                except Exception as e:
                    logger.error(f"销毁任务 {task._id} 错误: {e}")
        cls._registry.clear()
        logger.info("所有 Redis 流任务已销毁")
