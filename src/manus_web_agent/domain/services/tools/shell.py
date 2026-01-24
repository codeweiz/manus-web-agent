from typing import Optional

from manus_web_agent.domain.external.sandbox import Sandbox
from manus_web_agent.domain.models.tool_result import ToolResult
from manus_web_agent.domain.services.tools.base import BaseTool, tool


class ShellTool(BaseTool):
    """Shell 工具"""

    name: str = "shell"

    def __init__(self, sandbox: Sandbox):
        super().__init__()
        self.sandbox = sandbox

    @tool(
        name="shell_exec",
        description="Execute a shell command. Use for running shell commands.",
        parameters={
            "id": {
                "type": "string",
                "description": "ID of the shell session to execute the command in."
            },
            "exec_dir": {
                "type": "string",
                "description": "Directory to execute the command in."
            },
            "command": {
                "type": "string",
                "description": "Command to execute."
            }
        },
        required=["id", "exec_dir", "command"],
    )
    async def shell_exec(self, id: str, exec_dir: str, command: str) -> ToolResult:
        """执行命令
        :param id: 会话 ID
        :param exec_dir: 执行目录
        :param command: 命令
        :return: 执行结果
        """
        return await self.sandbox.exec_command(id, exec_dir, command)

    @tool(
        name="shell_view",
        description="View the shell session. Use for checking the latest state of previously executed commands.",
        parameters={
            "id": {
                "type": "string",
                "description": "ID of the shell session to view."
            }
        },
        required=["id"],
    )
    async def shell_view(self, id: str) -> ToolResult:
        """查看 Shell
        :param id: 会话 ID
        :return: 查看结果
        """
        return await self.sandbox.view_shell(id)

    @tool(
        name="shell_wait",
        description="Wait for the shell session to finish. Use for waiting for a command to finish executing.",
        parameters={
            "id": {
                "type": "string",
                "description": "ID of the shell session to wait for."
            },
            "seconds": {
                "type": "integer",
                "description": "Optional. Number of seconds to wait for the command to finish executing."
            }
        },
        required=["id"],
    )
    async def shell_wait(self, id: str, seconds: Optional[int] = None) -> ToolResult:
        """等待进程
        :param id: 会话 ID
        :param seconds: 等待秒数
        :return: 等待结果
        """
        return await self.sandbox.wait_for_process(id, seconds)

    @tool(
        name="shell_write_process",
        description="Write to the shell session. Use for writing to a command that is waiting for input.",
        parameters={
            "id": {
                "type": "string",
                "description": "ID of the shell session to write to."
            },
            "input_text": {
                "type": "string",
                "description": "Text to write to the shell session."
            },
            "press_enter": {
                "type": "boolean",
                "description": "Optional. Whether to press enter after writing the text."
            }
        },
        required=["id", "input_text"],
    )
    async def shell_write_process(self, id: str, input_text: str, press_enter: bool = True):
        """写入到进程
        :param id: 会话 ID
        :param input_text: 输入文本
        :param press_enter: 是否按下回车
        :return: 写入结果
        """
        return await self.sandbox.write_to_process(id, input_text, press_enter)

    @tool(
        name="shell_kill_process",
        description="Kill the shell session. Use for killing a command that is still running.",
        parameters={
            "id": {
                "type": "string",
                "description": "ID of the shell session to kill."
            }
        },
        required=["id"],
    )
    async def shell_kill_process(self, id: str) -> ToolResult:
        """杀死进程
        :param id: 会话 ID
        :return: 杀死结果
        """
        return await self.sandbox.kill_process(id)
