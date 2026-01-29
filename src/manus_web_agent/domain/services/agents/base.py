import asyncio
import json
import logging
import uuid
from abc import ABC
from typing import Optional, List, Dict, Any, AsyncGenerator

from manus_web_agent.domain.external.llm import LLM
from manus_web_agent.domain.models.event import BaseEvent, ToolEvent, ToolStatus, ErrorEvent, MessageEvent
from manus_web_agent.domain.models.message import Message
from manus_web_agent.domain.models.tool_result import ToolResult
from manus_web_agent.domain.repositories.agent_repository import AgentRepository
from manus_web_agent.domain.services.tools.base import BaseTool
from manus_web_agent.domain.utils.json_parser import JsonParser

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """基础代理"""

    name: str = ""
    system_prompt: str = ""
    format: Optional[str] = None
    max_iterations: int = 100
    max_retries: int = 3
    retry_interval: float = 1.0
    tool_choice: Optional[str] = None

    def __init__(
            self,
            agent_id: str,
            agent_repository: AgentRepository,
            llm: LLM,
            json_parser: JsonParser,
            tools: List[BaseTool] = [],
    ):
        self._agent_id = agent_id
        self._agent_repository = agent_repository
        self._llm = llm
        self._json_parser = json_parser
        self._tools = tools
        self.memory = None

    def get_available_tools(self) -> Optional[List[Dict[str, Any]]]:
        """获取所有可用工具列表"""
        available_tools = []
        for tool in self._tools:
            available_tools.extend(tool.get_tools())
        return available_tools

    def get_tool(self, function_name: str) -> BaseTool:
        """获取指定工具"""
        for tool in self._tools:
            if tool.has_function(function_name):
                return tool
        raise ValueError(f"未知工具: {function_name}")

    async def invoke_tool(self, tool: BaseTool, function_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """调用指定工具，带重试机制"""

        retries = 0
        last_error = ""
        while retries <= self.max_retries:
            try:
                return await tool.invoke_function(function_name, **arguments)
            except Exception as e:
                last_error = str(e)
                retries += 1
                if retries <= self.max_retries:
                    await asyncio.sleep(self.retry_interval)
                else:
                    logger.exception(f"工具执行失败, {function_name}, {arguments}")
                    break

        return ToolResult(success=False, message=last_error)

    async def execute(self, request: str, format: Optional[str] = None) -> AsyncGenerator[BaseEvent, None]:
        """执行代理"""
        format = format or self.format
        message = await self.ask(request, format)
        for _ in range(self.max_iterations):
            if not message.get("tool_calls"):
                break
            tool_responses = []
            for tool_call in message["tool_calls"]:
                if not tool_call.get("function"):
                    continue

                function_name = tool_call["function"]["name"]
                tool_call_id = tool_call["id"] or str(uuid.uuid4())
                function_args = await self._json_parser.parse(tool_call["function"]["arguments"])

                tool = self.get_tool(function_name)

                # 生成事件（工具调用前）
                yield ToolEvent(
                    status=ToolStatus.CALLING,
                    tool_call_id=tool_call_id,
                    tool_name=tool.name,
                    function_name=function_name,
                    function_args=function_args
                )

                result = await self.invoke_tool(tool, function_name, function_args)

                # 生成事件（工具调用后）
                yield ToolEvent(
                    status=ToolStatus.CALLED,
                    tool_call_id=tool_call_id,
                    tool_name=tool.name,
                    function_name=function_name,
                    function_args=function_args,
                    function_result=result
                )

                tool_response = {
                    "role": "tool",
                    "function_name": function_name,
                    "tool_call_id": tool_call_id,
                    "content": result.model_dump_json()
                }
                tool_responses.append(tool_response)

            message = await self.ask_with_messages(tool_responses)
        else:
            yield ErrorEvent(error="达到最大迭代次数，未能完成任务")

        yield MessageEvent(message=message["content"])

    async def _ensure_memory(self):
        """确保记忆存在"""
        if not self.memory:
            self.memory = await self._agent_repository.get_memory(self._agent_id, self.name)

    async def _add_to_memory(self, messages: List[Dict[str, Any]]) -> None:
        """更新记忆并保存到仓库"""
        await self._ensure_memory()
        if self.memory.empty:
            self.memory.add_message({
                "role": "system", "content": self.system_prompt,
            })
        self.memory.add_messages(messages)
        await self._agent_repository.save_memory(self._agent_id, self.name, self.memory)

    async def _roll_back_memory(self) -> None:
        """回滚记忆"""
        await self._ensure_memory()
        self.memory.roll_back()
        await self._agent_repository.save_memory(self._agent_id, self.name, self.memory)

    async def ask_with_messages(self, messages: List[Dict[str, Any]], format: Optional[str] = None) -> Dict[str, Any]:
        """向 LLM 发送消息并获取响应"""
        await self._add_to_memory(messages)

        response_format = None
        if format:
            response_format = {"type": format}

        for _ in range(self.max_retries):
            message = await self._llm.ask(self.memory.get_messages(),
                                            tools=self.get_available_tools(),
                                            response_format=response_format,
                                            tool_choice=self.tool_choice)

            filtered_message = {}
            if message.get("role") == "assistant":
                if not message.get("content") and not message.get("tool_calls"):
                    logger.warning(f"助手消息为空，重试")
                    await self._add_to_memory([
                        {"role": "assistant", "content": ""},
                        {"role": "user", "content": "no thinking, please continue"}
                    ])
                    continue
                filtered_message = {
                    "role": "assistant",
                    "content": message.get("content"),
                }
                if message.get("tool_calls"):
                    filtered_message["tool_calls"] = message.get("tool_calls")[:1]
            else:
                logger.warning(f"未知消息角色: {message.get('role')}")
                filtered_message = message

            await self._add_to_memory([filtered_message])
            return filtered_message
        raise Exception(f"LLM 在 {self.max_retries} 次重试后返回空响应")

    async def ask(self, request: str, format: Optional[str] = None) -> Dict[str, Any]:
        """向 LLM 发送单个消息"""
        return await self.ask_with_messages([
            {
                "role": "user", "content": request
            }
        ], format)

    async def roll_back(self, message: Message):
        """回滚到指定消息"""
        await self._ensure_memory()
        last_message = self.memory.get_last_message()
        if (not last_message or
            not last_message.get("tool_calls") or
            len(last_message.get("tool_calls")) == 0):
            return
        tool_call = last_message.get("tool_calls")[0]
        function_name = tool_call.get("function", {}).get("name")
        tool_call_id = tool_call.get("id")
        if function_name == "message_ask_user":
            self.memory.add_message({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "function_name": function_name,
                "content": message.model_dump_json()
            })
        else:
            self.memory.roll_back()
        await self._agent_repository.save_memory(self._agent_id, self.name, self.memory)

    async def compact_memory(self) -> None:
        """压缩记忆"""
        await self._ensure_memory()
        self.memory.compact()
        await self._agent_repository.save_memory(self._agent_id, self.name, self.memory)
