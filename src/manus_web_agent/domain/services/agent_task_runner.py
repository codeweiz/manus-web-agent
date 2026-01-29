import asyncio
import logging
from typing import Optional, AsyncGenerator, List

from pydantic import TypeAdapter

from manus_web_agent.domain.external.browser import Browser
from manus_web_agent.domain.external.file import FileStorage
from manus_web_agent.domain.external.llm import LLM
from manus_web_agent.domain.external.sandbox import Sandbox
from manus_web_agent.domain.external.search import SearchEngine
from manus_web_agent.domain.external.task import TaskRunner, Task
from manus_web_agent.domain.models.event import (
    BaseEvent, ErrorEvent, TitleEvent, MessageEvent, DoneEvent, ToolEvent, WaitEvent,
    FileToolContent, ShellToolContent, SearchToolContent, BrowserToolContent,
    ToolStatus, AgentEvent, MCPToolContent
)
from manus_web_agent.domain.models.file import FileInfo
from manus_web_agent.domain.models.message import Message
from manus_web_agent.domain.models.search import SearchResults
from manus_web_agent.domain.models.session import SessionStatus
from manus_web_agent.domain.models.tool_result import ToolResult
from manus_web_agent.domain.repositories.agent_repository import AgentRepository
from manus_web_agent.domain.repositories.mcp_repository import MCPRepository
from manus_web_agent.domain.repositories.session_repository import SessionRepository
from manus_web_agent.domain.services.flows.plan_act import PlanActFlow
from manus_web_agent.domain.services.tools.mcp import MCPTool
from manus_web_agent.domain.utils.json_parser import JsonParser

logger = logging.getLogger(__name__)


class AgentTaskRunner(TaskRunner):
    """Agent 任务运行器，可取消的 Agent 任务"""

    def __init__(
            self,
            session_id: str,
            agent_id: str,
            user_id: str,
            llm: LLM,
            sandbox: Sandbox,
            browser: Browser,
            agent_repository: AgentRepository,
            session_repository: SessionRepository,
            json_parser: JsonParser,
            file_storage: FileStorage,
            mcp_repository: MCPRepository,
            search_engine: Optional[SearchEngine] = None,
    ):
        self._session_id = session_id
        self._agent_id = agent_id
        self._user_id = user_id
        self._llm = llm
        self._sandbox = sandbox
        self._browser = browser
        self._search_engine = search_engine
        self._agent_repository = agent_repository
        self._session_repository = session_repository
        self._json_parser = json_parser
        self._file_storage = file_storage
        self._mcp_repository = mcp_repository
        self._mcp_tool = MCPTool()
        self._flow = PlanActFlow(
            self._agent_id,
            self._agent_repository,
            self._session_id,
            self._session_repository,
            self._llm,
            self._sandbox,
            self._browser,
            self._json_parser,
            self._mcp_tool,
            self._search_engine,
        )

    async def _put_and_add_event(self, task: Task, event: AgentEvent) -> None:
        """发送事件并添加到会话"""
        event_id = await task.output_stream.put(event.model_dump_json())
        event.id = event_id
        await self._session_repository.add_event(self._session_id, event)

    async def _pop_event(self, task: Task) -> Optional[AgentEvent]:
        """从任务输入流弹出事件"""
        event_id, event_str = await task.input_stream.pop()
        if event_str is None:
            logger.warning(f"Agent {self._agent_id} 收到空消息")
            return None
        event = TypeAdapter(AgentEvent).validate_json(event_str)
        event.id = event_id
        return event

    async def _get_browser_screenshot(self) -> str:
        """获取浏览器截图并上传"""
        screenshot = await self._browser.screenshot()
        result = await self._file_storage.upload_file(screenshot, "screenshot.png", self._user_id)
        return result.file_id

    async def _sync_file_to_storage(self, file_path: str) -> Optional[FileInfo]:
        """将文件从沙箱同步到存储"""
        try:
            file_info = await self._session_repository.get_file_by_path(self._session_id, file_path)
            file_data = await self._sandbox.file_download(file_path)
            if file_info:
                await self._session_repository.remove_file(self._session_id, file_info.file_id)
            file_name = file_path.split("/")[-1]
            file_info = await self._file_storage.upload_file(file_data, file_name, self._user_id)
            file_info.file_path = file_path
            await self._session_repository.add_file(self._session_id, file_info)
            return file_info
        except Exception as e:
            logger.exception(f"Agent {self._agent_id} 同步文件失败: {e}")
            return None

    async def _sync_file_to_sandbox(self, file_id: str) -> Optional[FileInfo]:
        """将文件从存储下载到沙箱"""
        try:
            file_data, file_info = await self._file_storage.download_file(file_id, self._user_id)
            file_path = "/home/ubuntu/upload/" + file_info.filename
            result = await self._sandbox.file_upload(file_data, file_path)
            if result.success:
                file_info.file_path = file_path
                return file_info
        except Exception as e:
            logger.exception(f"Agent {self._agent_id} 同步文件到沙箱失败: {e}")
        return None

    async def _sync_message_attachments_to_sandbox(self, event: MessageEvent) -> None:
        """同步消息附件到沙箱"""
        attachments: List[FileInfo] = []
        try:
            if event.attachments:
                for attachment in event.attachments:
                    file_info = await self._sync_file_to_sandbox(attachment.file_id)
                    if file_info:
                        attachments.append(file_info)
                        await self._session_repository.add_file(self._session_id, file_info)
            event.attachments = attachments
        except Exception as e:
            logger.exception(f"Agent {self._agent_id} 同步附件到事件失败: {e}")

    async def _handle_tool_event(self, event: ToolEvent):
        """生成工具内容"""
        try:
            if event.status == ToolStatus.CALLED:
                if event.tool_name == "browser":
                    event.tool_content = BrowserToolContent(screenshot=await self._get_browser_screenshot())
                elif event.tool_name == "search":
                    search_results: ToolResult[SearchResults] = event.function_result
                    logger.debug(f"搜索工具结果: {search_results}")
                    if search_results.data and hasattr(search_results.data, 'results'):
                        event.tool_content = SearchToolContent(results=search_results.data.results)
                    else:
                        event.tool_content = SearchToolContent(results=[])
                elif event.tool_name == "shell":
                    if "id" in event.function_args:
                        shell_result = await self._sandbox.view_shell(event.function_args["id"], console=True)
                        event.tool_content = ShellToolContent(console=shell_result.data.get("console", []))
                    else:
                        event.tool_content = ShellToolContent(console="(无控制台)")
                elif event.tool_name == "file":
                    if "file" in event.function_args:
                        file_path = event.function_args["file"]
                        file_read_result = await self._sandbox.file_read(file_path)
                        file_content: str = file_read_result.data.get("content", "")
                        event.tool_content = FileToolContent(content=file_content)
                        await self._sync_file_to_storage(file_path)
                    else:
                        event.tool_content = FileToolContent(content="(无内容)")
                elif event.tool_name == "mcp":
                    logger.debug(f"处理 MCP 工具事件: function_result={event.function_result}")
                    if event.function_result:
                        if hasattr(event.function_result, 'data') and event.function_result.data:
                            logger.debug(f"MCP 工具结果数据: {event.function_result.data}")
                            event.tool_content = MCPToolContent(result=event.function_result.data)
                        elif hasattr(event.function_result, 'success') and event.function_result.success:
                            logger.debug(f"MCP 工具结果 (成功，无数据): {event.function_result}")
                            result_data = event.function_result.model_dump() if hasattr(event.function_result, 'model_dump') else str(event.function_result)
                            event.tool_content = MCPToolContent(result=result_data)
                        else:
                            logger.debug(f"MCP 工具结果 (回退): {event.function_result}")
                            event.tool_content = MCPToolContent(result=str(event.function_result))
                    else:
                        logger.warning("MCP 工具: 未找到 function_result")
                        event.tool_content = MCPToolContent(result="无可用结果")

                    logger.debug(f"MCP tool_content 设置为: {event.tool_content}")
                    if event.tool_content:
                        logger.debug(f"MCP tool_content.result: {event.tool_content.result}")
                        logger.debug(f"MCP tool_content dict: {event.tool_content.model_dump()}")
                else:
                    logger.warning(f"Agent {self._agent_id} 收到未知工具事件: {event.tool_name}")
        except Exception as e:
            logger.exception(f"Agent {self._agent_id} 生成工具内容失败: {e}")

    async def run(self, task: Task) -> None:
        """处理 Agent 的消息队列并运行 Agent 流程"""
        try:
            logger.info(f"Agent {self._agent_id} 消息处理任务开始")
            await self._sandbox.ensure_sandbox()
            await self._mcp_tool.initialized(await self._mcp_repository.get_mcp_config())
            while not await task.input_stream.is_empty():
                event = await self._pop_event(task)
                if event is None:
                    continue
                message = ""
                if isinstance(event, MessageEvent):
                    message = event.message or ""
                    await self._sync_message_attachments_to_sandbox(event)

                logger.info(f"Agent {self._agent_id} 收到新消息: {message[:50]}...")

                message_obj = Message(message=message, attachments=[attachment.file_path for attachment in event.attachments] if event.attachments else [])

                async for ev in self._run_flow(message_obj):
                    await self._put_and_add_event(task, ev)
                    if isinstance(ev, TitleEvent):
                        await self._session_repository.update_title(self._session_id, ev.title)
                    elif isinstance(ev, MessageEvent):
                        await self._session_repository.update_latest_message(self._session_id, ev.message, ev.timestamp)
                        await self._session_repository.increment_unread_message_count(self._session_id)
                    elif isinstance(ev, WaitEvent):
                        await self._session_repository.update_status(self._session_id, SessionStatus.WAITING)
                        return
                    if not await task.input_stream.is_empty():
                        break

            await self._session_repository.update_status(self._session_id, SessionStatus.COMPLETED)
        except asyncio.CancelledError:
            logger.info(f"Agent {self._agent_id} 任务被取消")
            await self._put_and_add_event(task, DoneEvent())
            await self._session_repository.update_status(self._session_id, SessionStatus.COMPLETED)
        except Exception as e:
            logger.exception(f"Agent {self._agent_id} 任务遇到异常: {str(e)}")
            await self._put_and_add_event(task, ErrorEvent(error=f"任务错误: {str(e)}"))
            await self._session_repository.update_status(self._session_id, SessionStatus.COMPLETED)

    async def _run_flow(self, message: Message) -> AsyncGenerator[BaseEvent, None]:
        """通过 Agent 流程处理单条消息并产生事件"""
        if not message.message:
            logger.warning(f"Agent {self._agent_id} 收到空消息")
            yield ErrorEvent(error="无消息")
            return

        async for event in self._flow.run(message):
            if isinstance(event, ToolEvent):
                await self._handle_tool_event(event)
            elif isinstance(event, MessageEvent):
                pass  # 处理消息事件如果需要
            yield event

        logger.info(f"Agent {self._agent_id} 完成处理一条消息")

    async def on_done(self, task: Task) -> None:
        """任务完成时调用"""
        logger.info(f"Agent {self._agent_id} 任务完成")

    async def destroy(self) -> None:
        """销毁任务并释放资源"""
        logger.info(f"开始销毁 Agent 任务")

        # 销毁沙箱环境
        if self._sandbox:
            logger.debug(f"销毁 Agent {self._agent_id} 的沙箱环境")
            await self._sandbox.destroy()

        if self._mcp_tool:
            logger.debug(f"销毁 Agent {self._agent_id} 的 MCP 工具")
            await self._mcp_tool.cleanup()

        logger.debug(f"Agent {self._agent_id} 已完全关闭并清理资源")
