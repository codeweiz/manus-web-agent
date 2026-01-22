from abc import ABC, abstractmethod
from typing import Protocol, Optional

from manus_web_agent.domain.external.message_queue import MessageQueue


class Task(Protocol):
    """任务"""

    async def run(self) -> None:
        """运行任务"""
        pass

    def cancel(self) -> bool:
        """取消任务"""
        pass

    @property
    def input_stream(self) -> MessageQueue:
        """获取输入流"""
        pass

    @property
    def output_stream(self) -> MessageQueue:
        """获取输出流"""
        pass

    @property
    def id(self) -> str:
        """获取任务 ID"""
        pass

    @property
    def done(self) -> bool:
        """检查任务是否完成"""
        pass

    @classmethod
    def get(cls, task_id: str) -> Optional['Task']:
        """获取任务
        :param task_id: 任务 ID
        :return: 任务
        """
        pass

    @classmethod
    def create(cls, runner: 'TaskRunner') -> 'Task':
        """创建任务
        :param runner: 任务执行器
        :return: 任务
        """
        pass

    @classmethod
    async def destroy(cls) -> None:
        """销毁任务"""
        pass


class TaskRunner(ABC):
    """任务执行器"""

    @abstractmethod
    async def run(self, task: 'Task') -> None:
        """运行任务"""
        pass

    @abstractmethod
    async def destroy(self) -> None:
        """销毁"""
        pass

    @abstractmethod
    async def on_done(self, task: 'Task') -> None:
        """当任务完成时调用"""
        pass
