"""会话路由"""

import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator, List, Optional

import websockets
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from manus_web_agent.application.errors.exceptions import NotFoundError, UnauthorizedError
from manus_web_agent.application.services.agent_service import AgentService
from manus_web_agent.application.services.file_service import FileService
from manus_web_agent.domain.models.file import FileInfo
from manus_web_agent.interfaces.dependencies import (
    get_agent_service,
    get_current_user,
    get_file_service,
    get_optional_current_user,
    get_token_service,
    verify_signature_websocket,
)
from manus_web_agent.interfaces.schemas.base import APIResponse
from manus_web_agent.interfaces.schemas.event import EventMapper
from manus_web_agent.interfaces.schemas.file import FileViewRequest, FileViewResponse
from manus_web_agent.interfaces.schemas.resource import AccessTokenRequest, SignedUrlResponse
from manus_web_agent.interfaces.schemas.session import (
    ChatRequest,
    CreateSessionResponse,
    GetSessionResponse,
    ListSessionItem,
    ListSessionResponse,
    ShareSessionResponse,
    SharedSessionResponse,
    ShellViewRequest,
    ShellViewResponse,
)

logger = logging.getLogger(__name__)
SESSION_POLL_INTERVAL = 5

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.put("", response_model=APIResponse[CreateSessionResponse])
async def create_session(
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse[CreateSessionResponse]:
    """创建新会话"""
    session = await agent_service.create_session(current_user.get("id"))
    return APIResponse.success(CreateSessionResponse(session_id=session.id))


@router.get("/{session_id}", response_model=APIResponse[GetSessionResponse])
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse[GetSessionResponse]:
    """获取会话详情"""
    session = await agent_service.get_session(session_id, current_user.get("id"))
    if not session:
        raise NotFoundError("会话不存在")
    return APIResponse.success(
        GetSessionResponse(
            session_id=session.id,
            title=session.title,
            status=session.status,
            events=await EventMapper.events_to_sse_events(session.events),
            is_shared=session.is_shared,
        )
    )


@router.delete("/{session_id}", response_model=APIResponse[None])
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse[None]:
    """删除会话"""
    success = await agent_service.delete_session(session_id, current_user.get("id"))
    if not success:
        raise NotFoundError("会话不存在")
    return APIResponse.success()


@router.post("/{session_id}/stop", response_model=APIResponse[None])
async def stop_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse[None]:
    """停止会话"""
    await agent_service.stop_session(session_id, current_user.get("id"))
    return APIResponse.success()


@router.post("/{session_id}/clear_unread_message_count", response_model=APIResponse[None])
async def clear_unread_message_count(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse[None]:
    """清除未读消息计数"""
    await agent_service.clear_unread_message_count(session_id, current_user.get("id"))
    return APIResponse.success()


@router.get("", response_model=APIResponse[ListSessionResponse])
async def get_all_sessions(
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse[ListSessionResponse]:
    """获取所有会话"""
    sessions = await agent_service.get_all_sessions(current_user.get("id"))
    session_items = [
        ListSessionItem(
            session_id=session.id,
            title=session.title,
            status=session.status,
            unread_message_count=session.unread_message_count,
            latest_message=session.latest_message,
            latest_message_at=int(session.latest_message_at.timestamp())
            if session.latest_message_at
            else None,
            is_shared=session.is_shared,
        )
        for session in sessions
    ]
    return APIResponse.success(ListSessionResponse(sessions=session_items))


@router.post("")
async def stream_sessions(
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> EventSourceResponse:
    """流式获取会话列表（SSE）"""

    async def event_generator() -> AsyncGenerator[ServerSentEvent, None]:
        while True:
            sessions = await agent_service.get_all_sessions(current_user.get("id"))
            session_items = [
                ListSessionItem(
                    session_id=session.id,
                    title=session.title,
                    status=session.status,
                    unread_message_count=session.unread_message_count,
                    latest_message=session.latest_message,
                    latest_message_at=int(session.latest_message_at.timestamp())
                    if session.latest_message_at
                    else None,
                    is_shared=session.is_shared,
                )
                for session in sessions
            ]
            yield ServerSentEvent(
                event="sessions",
                data=ListSessionResponse(sessions=session_items).model_dump_json(),
            )
            await asyncio.sleep(SESSION_POLL_INTERVAL)

    return EventSourceResponse(event_generator())


@router.post("/{session_id}/chat")
async def chat(
    session_id: str,
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> EventSourceResponse:
    """聊天 SSE 流"""

    async def event_generator() -> AsyncGenerator[ServerSentEvent, None]:
        async for event in agent_service.chat(
            session_id=session_id,
            user_id=current_user.get("id"),
            message=request.message,
            timestamp=datetime.fromtimestamp(request.timestamp) if request.timestamp else None,
            event_id=request.event_id,
            attachments=request.attachments,
        ):
            logger.debug(f"从聊天收到事件: {event}")
            sse_event = await EventMapper.event_to_sse_event(event)
            logger.debug(f"转换后的 SSE 事件: {sse_event}")
            if sse_event:
                yield ServerSentEvent(
                    event=sse_event.event,
                    data=sse_event.data.model_dump_json() if sse_event.data else None,
                )

    return EventSourceResponse(event_generator())


@router.post("/{session_id}/shell")
async def view_shell(
    session_id: str,
    request: ShellViewRequest,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse[ShellViewResponse]:
    """查看 Shell 会话输出"""
    result = await agent_service.shell_view(
        session_id, request.session_id, current_user.get("id")
    )
    return APIResponse.success(result)


@router.post("/{session_id}/file")
async def view_file(
    session_id: str,
    request: FileViewRequest,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse[FileViewResponse]:
    """查看文件内容"""
    result = await agent_service.file_view(
        session_id, request.file, current_user.get("id")
    )
    return APIResponse.success(result)


@router.websocket("/{session_id}/vnc")
async def vnc_websocket(
    websocket: WebSocket,
    session_id: str,
    signature: str = Depends(verify_signature_websocket),
    agent_service: AgentService = Depends(get_agent_service),
) -> None:
    """VNC WebSocket 端点（二进制模式）"""

    await websocket.accept(subprotocol="binary")
    logger.info(f"接受 WebSocket 连接，会话 {session_id}")

    try:
        sandbox_ws_url = await agent_service.get_vnc_url(session_id, None)

        logger.info(f"连接到 VNC WebSocket: {sandbox_ws_url}")

        async with websockets.connect(sandbox_ws_url) as sandbox_ws:
            logger.info(f"已连接到 VNC WebSocket: {sandbox_ws_url}")

            async def forward_to_sandbox():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        await sandbox_ws.send(data)
                except WebSocketDisconnect:
                    logger.info("Web -> VNC 连接关闭")
                except Exception as e:
                    logger.error(f"转发数据到沙箱出错: {e}")

            async def forward_from_sandbox():
                try:
                    while True:
                        data = await sandbox_ws.recv()
                        await websocket.send_bytes(data)
                except websockets.exceptions.ConnectionClosed:
                    logger.info("VNC -> Web 连接关闭")
                except Exception as e:
                    logger.error(f"从沙箱转发数据出错: {e}")

            forward_task1 = asyncio.create_task(forward_to_sandbox())
            forward_task2 = asyncio.create_task(forward_from_sandbox())

            done, pending = await asyncio.wait(
                [forward_task1, forward_task2], return_when=asyncio.FIRST_COMPLETED
            )

            logger.info("WebSocket 连接关闭")

            for task in pending:
                task.cancel()

    except ConnectionError as e:
        logger.error(f"无法连接到沙箱环境: {str(e)}")
        await websocket.close(code=1011, reason=f"无法连接到沙箱环境: {str(e)}")
    except Exception as e:
        logger.error(f"WebSocket 错误: {str(e)}")
        await websocket.close(code=1011, reason=f"WebSocket 错误: {str(e)}")


@router.get("/{session_id}/files")
async def get_session_files(
    session_id: str,
    current_user: Optional[dict] = Depends(get_optional_current_user),
    agent_service: AgentService = Depends(get_agent_service),
    file_service: FileService = Depends(get_file_service),
) -> APIResponse[List[FileInfo]]:
    """获取会话文件列表"""
    if not current_user and not await agent_service.is_session_shared(session_id):
        raise UnauthorizedError()

    files = await agent_service.get_session_files(
        session_id, current_user.get("id") if current_user else None
    )

    # 为每个文件添加 URL
    for file in files:
        await file_service.enrich_with_file_url(file)

    return APIResponse.success(files)


@router.post("/{session_id}/vnc/signed-url", response_model=APIResponse[SignedUrlResponse])
async def create_vnc_signed_url(
    session_id: str,
    request_data: AccessTokenRequest,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse[SignedUrlResponse]:
    """为 VNC WebSocket 访问生成签名 URL"""

    expire_minutes = request_data.expire_minutes
    if expire_minutes > 15:
        expire_minutes = 15

    session = await agent_service.get_session(session_id, current_user.get("id"))
    if not session:
        raise NotFoundError("会话不存在")

    from manus_web_agent.application.services.token_service import TokenService

    token_service = TokenService()
    ws_base_url = f"/api/v1/sessions/{session_id}/vnc"
    signed_url = token_service.create_signed_url(ws_base_url, expire_minutes)

    logger.info(
        f"为用户 {current_user.get('id')}，会话 {session_id} 创建 VNC 签名 URL"
    )

    return APIResponse.success(
        SignedUrlResponse(signed_url=signed_url, expires_in=expire_minutes * 60)
    )


@router.post("/{session_id}/share", response_model=APIResponse[ShareSessionResponse])
async def share_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse[ShareSessionResponse]:
    """分享会话"""
    await agent_service.share_session(session_id, current_user.get("id"))
    return APIResponse.success(
        ShareSessionResponse(session_id=session_id, is_shared=True)
    )


@router.get("/{session_id}/share/files")
async def get_shared_session_files(
    session_id: str,
    agent_service: AgentService = Depends(get_agent_service),
    file_service: FileService = Depends(get_file_service),
) -> APIResponse[List[FileInfo]]:
    """获取共享会话的文件"""
    files = await agent_service.get_shared_session_files(session_id)
    for file in files:
        await file_service.enrich_with_file_url(file)
    return APIResponse.success(files)


@router.delete("/{session_id}/share", response_model=APIResponse[ShareSessionResponse])
async def unshare_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse[ShareSessionResponse]:
    """取消分享会话"""
    await agent_service.unshare_session(session_id, current_user.get("id"))
    return APIResponse.success(
        ShareSessionResponse(session_id=session_id, is_shared=False)
    )


@router.get("/shared/{session_id}", response_model=APIResponse[SharedSessionResponse])
async def get_shared_session(
    session_id: str,
    agent_service: AgentService = Depends(get_agent_service),
) -> APIResponse[SharedSessionResponse]:
    """无需认证获取共享会话"""
    session = await agent_service.get_shared_session(session_id)
    if not session:
        raise NotFoundError("共享会话不存在")

    return APIResponse.success(
        SharedSessionResponse(
            session_id=session.id,
            title=session.title,
            status=session.status,
            events=await EventMapper.events_to_sse_events(session.events),
            is_shared=session.is_shared,
        )
    )
