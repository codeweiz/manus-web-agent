import logging
from typing import List, Dict, Any

from pydantic import BaseModel, Field

from manus_web_agent.domain.models.tool_result import ToolResult

logger = logging.getLogger(__name__)


class Memory(BaseModel):
    """记忆"""

    messages: List[Dict[str, Any]] = Field(default_factory=list, description="消息列表")

    def get_message_role(self, message: Dict[str, Any]) -> str:
        """获取消息中的角色"""
        return message.get("role")

    def add_message(self, message: Dict[str, Any]) -> None:
        """向消息列表中添加消息"""
        self.messages.append(message)

    def add_messages(self, messages: List[Dict[str, Any]]) -> None:
        """向消息列表中添加消息列表"""
        self.messages.extend(messages)

    def get_messages(self) -> List[Dict[str, Any]]:
        """获取消息列表"""
        return self.messages

    def get_last_message(self) -> Dict[str, Any]:
        """获取消息列表中最后一个消息"""
        return self.messages[-1] if len(self.messages) > 0 else None

    def roll_back(self) -> None:
        """回退一步"""
        self.messages = self.messages[:-1]

    def compact(self) -> None:
        """压缩消息列表"""
        for message in self.messages:
            if message.get("role") == "tool":
                if message.get("function_name") in ["browse_view", "browser_navigate"]:
                    message["content"] = ToolResult(success=True, data='(removed)').model_dump_json()
                    logger.debug(f"Removed tool result from memory: {message['function_name']}")

    @property
    def empty(self) -> bool:
        """检查消息是否为空"""
        return len(self.messages) == 0
