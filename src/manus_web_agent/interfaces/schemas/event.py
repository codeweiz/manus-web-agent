from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field

from manus_web_agent.domain.models.event import (
    AgentEvent, BaseEvent, MessageEvent, ToolEvent, StepEvent, PlanEvent,
    TitleEvent, ErrorEvent, DoneEvent, WaitEvent, ToolStatus
)


class BaseEventData(BaseModel):
    """基础事件数据"""
    event_id: Optional[str] = Field(default=None, description="事件 ID")
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp()), description="时间戳")


class BaseSSEEvent(BaseModel):
    """基础 SSE 事件"""
    event: str = Field(..., description="事件类型")
    data: BaseEventData = Field(..., description="事件数据")


class MessageEventData(BaseEventData):
    """消息事件数据"""
    role: Optional[str] = Field(default=None, description="角色")
    content: Optional[str] = Field(default=None, description="内容")
    attachments: Optional[List[Dict[str, Any]]] = Field(default=None, description="附件")


class MessageSSEEvent(BaseSSEEvent):
    """消息 SSE 事件"""
    event: str = "message"
    data: MessageEventData


class ToolEventData(BaseEventData):
    """工具事件数据"""
    tool_call_id: Optional[str] = Field(default=None, description="工具调用 ID")
    name: Optional[str] = Field(default=None, description="工具名称")
    status: str = Field(..., description="状态")
    function: Optional[str] = Field(default=None, description="函数名")
    args: Optional[Dict[str, Any]] = Field(default=None, description="参数")
    content: Optional[Dict[str, Any]] = Field(default=None, description="内容")


class ToolSSEEvent(BaseSSEEvent):
    """工具 SSE 事件"""
    event: str = "tool"
    data: ToolEventData


class StepEventData(BaseEventData):
    """步骤事件数据"""
    status: str = Field(..., description="状态")
    step_id: Optional[str] = Field(default=None, description="步骤 ID")
    description: Optional[str] = Field(default=None, description="描述")


class StepSSEEvent(BaseSSEEvent):
    """步骤 SSE 事件"""
    event: str = "step"
    data: StepEventData


class TitleEventData(BaseEventData):
    """标题事件数据"""
    title: str = Field(..., description="标题")


class TitleSSEEvent(BaseSSEEvent):
    """标题 SSE 事件"""
    event: str = "title"
    data: TitleEventData


class PlanEventData(BaseEventData):
    """计划事件数据"""
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="步骤列表")


class PlanSSEEvent(BaseSSEEvent):
    """计划 SSE 事件"""
    event: str = "plan"
    data: PlanEventData


class ErrorEventData(BaseEventData):
    """错误事件数据"""
    error: str = Field(..., description="错误信息")


class ErrorSSEEvent(BaseSSEEvent):
    """错误 SSE 事件"""
    event: str = "error"
    data: ErrorEventData


class DoneSSEEvent(BaseSSEEvent):
    """完成 SSE 事件"""
    event: str = "done"
    data: BaseEventData


class WaitSSEEvent(BaseSSEEvent):
    """等待 SSE 事件"""
    event: str = "wait"
    data: BaseEventData


class EventMapper:
    """事件映射器"""

    @staticmethod
    async def event_to_sse_event(event: AgentEvent) -> Optional[BaseSSEEvent]:
        """将 AgentEvent 转换为 SSE 事件

        :param event: Agent 事件
        :return: SSE 事件
        """
        base_data = {"event_id": event.id, "timestamp": int(event.timestamp.timestamp()) if event.timestamp else int(datetime.now().timestamp())}

        if isinstance(event, MessageEvent):
            return MessageSSEEvent(
                data=MessageEventData(
                    **base_data,
                    role=event.role,
                    content=event.message,
                    attachments=[att.model_dump() for att in event.attachments] if event.attachments else None
                )
            )
        elif isinstance(event, ToolEvent):
            return ToolSSEEvent(
                data=ToolEventData(
                    **base_data,
                    tool_call_id=event.tool_call_id,
                    name=event.tool_name,
                    status=event.status.value if event.status else ToolStatus.CALLING.value,
                    function=event.function_name,
                    args=event.function_args,
                    content=event.tool_content.model_dump() if event.tool_content else None
                )
            )
        elif isinstance(event, StepEvent):
            return StepSSEEvent(
                data=StepEventData(
                    **base_data,
                    status=event.status.value,
                    step_id=event.step.id if event.step else None,
                    description=event.step.description if event.step else None
                )
            )
        elif isinstance(event, TitleEvent):
            return TitleSSEEvent(
                data=TitleEventData(
                    **base_data,
                    title=event.title
                )
            )
        elif isinstance(event, PlanEvent):
            return PlanSSEEvent(
                data=PlanEventData(
                    **base_data,
                    steps=[step.model_dump() for step in event.plan.steps] if event.plan else []
                )
            )
        elif isinstance(event, ErrorEvent):
            return ErrorSSEEvent(
                data=ErrorEventData(
                    **base_data,
                    error=event.error
                )
            )
        elif isinstance(event, DoneEvent):
            return DoneSSEEvent(data=BaseEventData(**base_data))
        elif isinstance(event, WaitEvent):
            return WaitSSEEvent(data=BaseEventData(**base_data))

        return None

    @staticmethod
    async def events_to_sse_events(events: List[AgentEvent]) -> List[BaseSSEEvent]:
        """批量转换事件为 SSE 事件

        :param events: 事件列表
        :return: SSE 事件列表
        """
        result = []
        for event in events:
            sse_event = await EventMapper.event_to_sse_event(event)
            if sse_event:
                result.append(sse_event)
        return result
