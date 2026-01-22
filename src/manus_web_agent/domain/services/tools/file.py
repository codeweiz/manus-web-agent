from typing import Optional

from manus_web_agent.domain.external.sandbox import Sandbox
from manus_web_agent.domain.models.tool_result import ToolResult
from manus_web_agent.domain.services.tools.base import BaseTool, tool


class FileTool(BaseTool):
    """文件工具"""

    name: str = "file"

    def __init__(self, sandbox: Sandbox):
        super().__init__()
        self.sandbox = sandbox

    @tool(
        name="file_read",
        description="Read the content of a file. Use for reading the content of a file.",
        parameters={
            "file": {
                "type": "string",
                "description": "Path to the file to read."
            },
            "start_line": {
                "type": "integer",
                "description": "Optional. Start line number to read from. If not specified, read from the beginning of the file."
            },
            "end_line": {
                "type": "integer",
                "description": "Optional. End line number to read to. If not specified, read to the end of the file."
            },
            "sudo": {
                "type": "boolean",
                "description": "Optional. Whether to use sudo to read the file."
            }
        },
        required=["file"],
    )
    async def file_read(
            self,
            file: str,
            start_line: Optional[int] = None,
            end_line: Optional[int] = None,
            sudo: bool = False
    ) -> ToolResult:
        """读取文件内容"""
        return await self.sandbox.file_read(file, start_line, end_line, sudo)

    @tool(
        name="file_write",
        description="Write content to a file. Use for writing content to a file.",
        parameters={
            "file": {
                "type": "string",
                "description": "Path to the file to write to."
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file."
            },
            "append": {
                "type": "boolean",
                "description": "Optional. Whether to append to the file instead of overwriting it."
            },
            "leading_newline": {
                "type": "boolean",
                "description": "Optional. Whether to add a newline before the content."
            },
            "trailing_newline": {
                "type": "boolean",
                "description": "Optional. Whether to add a newline after the content."
            },
            "sudo": {
                "type": "boolean",
                "description": "Optional. Whether to use sudo to write to the file."
            }
        },
        required=["file", "content"],
    )
    async def file_write(
            self,
            file: str,
            content: str,
            append: Optional[bool] = False,
            leading_newline: Optional[bool] = False,
            trailing_newline: Optional[bool] = False,
            sudo: Optional[bool] = False,
    ) -> ToolResult:
        """写入内容到文件"""
        return await self.sandbox.file_write(file, content, append, leading_newline, trailing_newline, sudo)

    @tool(
        name="file_str_replace",
        description="Replace a string in a file. Use for replacing a string in a file.",
        parameters={
            "file": {
                "type": "string",
                "description": "Path to the file to replace the string in."
            },
            "old_str": {
                "type": "string",
                "description": "String to replace."
            },
            "new_str": {
                "type": "string",
                "description": "New string to replace the old string with."
            },
            "sudo": {
                "type": "boolean",
                "description": "Optional. Whether to use sudo to replace the string in the file."
            }
        },
        required=["file", "old_str", "new_str"],
    )
    async def file_str_replace(self, file: str, old_str: str, new_str: str, sudo: Optional[bool] = False) -> ToolResult:
        """替换文件内容"""
        return await self.sandbox.file_replaces(file, old_str, new_str, sudo)

    @tool(
        name="file_find_in_content",
        description="Find a string in a file. Use for finding a string in a file.",
        parameters={
            "file": {
                "type": "string",
                "description": "Path to the file to find the string in."
            },
            "regex": {
                "type": "string",
                "description": "Regular expression to find."
            },
            "sudo": {
                "type": "boolean",
                "description": "Optional. Whether to use sudo to find the string in the file."
            }
        },
        required=["file", "regex"],
    )
    async def file_find_in_content(
            self,
            file: str,
            regex: str,
            sudo: Optional[bool] = False
    ) -> ToolResult:
        """搜索文件内容"""
        return await self.sandbox.file_search(file, regex, sudo)

    @tool(
        name="file_find_by_name",
        description="Find a file by name. Use for finding a file by name.",
        parameters={
            "path": {
                "type": "string",
                "description": "Path to search for the file in."
            },
            "glob_pattern": {
                "type": "string",
                "description": "Glob pattern to match the file name against."
            }
        },
        required=["path", "glob_pattern"],
    )
    async def file_find_by_name(
            self,
            path: str,
            glob_pattern: str
    ) -> ToolResult:
        """查找文件"""
        return await self.sandbox.file_find(path, glob_pattern)
