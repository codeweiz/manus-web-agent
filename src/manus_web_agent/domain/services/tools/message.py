from typing import Optional, Union, List

from manus_web_agent.domain.models.tool_result import ToolResult
from manus_web_agent.domain.services.tools.base import BaseTool, tool


class MessageTool(BaseTool):
    """消息工具"""

    name: str = "message"

    def __init__(self):
        super().__init__()

    @tool(
        name="message_notify_user",
        description="Send a message to user without requiring a response. Use for acknowledging receipt of messages, providing progress updates, reporting task completion, or explaining changes in approach.",
        parameters={"text": {"type": "string", "description": "Text to notify the user with."}},
        required=["text"],
    )
    async def message_notify_user(self, text: str):
        """通知用户
        :param text: 通知文本
        """

        return ToolResult(success=True, data=text)

    @tool(
        name="message_ask_user",
        description="Send a message to user and require a response. Use for clarifying ambiguity, seeking confirmation, or delegating decision-making to the user.",
        parameters={
            "text": {
                "type": "string",
                "description": "Text to ask the user."
            },
            "attachments": {
                "type": "array",
                "description": "Optional. Attachments to send with the message."
            },
            "suggest_user_takeover": {
                "type": "boolean",
                "description": "Optional. Whether to suggest the user to take over the conversation."
            }
        },
        required=["text"],
    )
    async def message_ask_user(
            self,
            text: str,
            attachments: Optional[Union[str, List[str]]] = None,
            suggest_user_takeover: Optional[str] = None
    ) -> ToolResult:
        """询问用户
        :param text: 问题文本
        :param attachments: 附件
        :param suggest_user_takeover: 建议用户接管
        """

        return ToolResult(success=True)
