from abc import ABC, abstractmethod
from typing import AsyncGenerator

from manus_web_agent.domain.models.event import BaseEvent


class BaseFlow(ABC):
    """基础流程"""

    @abstractmethod
    def run(self) -> AsyncGenerator[BaseEvent, None]:
        pass

    @abstractmethod
    def is_done(self) -> bool:
        pass
