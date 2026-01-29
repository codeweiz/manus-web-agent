import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator, List, Optional

import websockets
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from manus_web_agent.domain.services.agent_domain_service import AgentDomainService
from manus_web_agent.interfaces.dependencies import (
    get_agent_domain_service,
    get_current_user,
    get_optional_current_user,
    verify_signature_websocket,
)
from manus_web_agent.interfaces.schemas.base import APIResponse
from manus_web_agent.interfaces.schemas.event import EventMapper
from manus_web_agent.interfaces.schemas.file import FileViewRequest, FileViewResponse
from manus_web_agent.interfaces.schemas.resource import AccessTokenRequest, SignedUrlResponse
from manus_web_agent.interfaces.schemas.session import (
    ChatRequest,
    ConsoleRecord,
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
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[CreateSessionResponse]:
    """创建新会话"""
    # TODO: 实现创建会话逻辑
    session_id = "temp_session_id"
    return APIResponse.success(CreateSessionResponse(session_id=session_id))


@router.get("/{session_id}", response_model=APIResponse[GetSessionResponse])
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[GetSessionResponse]:
    """获取会话详情"""
    # TODO: 实现获取会话逻辑
    return APIResponse.success(
        GetSessionResponse(
            session_id=session_id,
            title="Test Session",
            status="pending",
            events=[],
            is_shared=False,
        )
    )


@router.delete("/{session_id}", response_model=APIResponse[None])
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[None]:
    """删除会话"""
    # TODO: 实现删除会话逻辑
    return APIResponse.success()


@router.post("/{session_id}/stop", response_model=APIResponse[None])
async def stop_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[None]:
    """停止会话"""
    await agent_service.stop_session(session_id)
    return APIResponse.success()


@router.post("/{session_id}/clear_unread_message_count", response_model=APIResponse[None])
async def clear_unread_message_count(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[None]:
    """清除未读消息计数"""
    # TODO: 实现清除未读消息计数逻辑
    return APIResponse.success()


@router.get("", response_model=APIResponse[ListSessionResponse])
async def get_all_sessions(
    current_user: dict = Depends(get_current_user),
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[ListSessionResponse]:
    """获取所有会话"""
    # TODO: 实现获取所有会话逻辑
    return APIResponse.success(ListSessionResponse(sessions=[]))


@router.post("")
async def stream_sessions(
    current_user: dict = Depends(get_current_user),
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> EventSourceResponse:
    """流式获取会话列表（SSE）"""

    async def event_generator() -> AsyncGenerator[ServerSentEvent, None]:
        while True:
            # TODO: 实现获取会话列表逻辑
            session_items: List[ListSessionItem] = []
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
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> EventSourceResponse:
    """聊天 SSE 流"""

    async def event_generator() -> AsyncGenerator[ServerSentEvent, None]:
        async for event in agent_service.chat(
            session_id=session_id,
            user_id=current_user.get("id"),
            message=request.message,
            timestamp=datetime.fromtimestamp(request.timestamp) if request.timestamp else None,
            latest_event_id=request.event_id,
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
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[ShellViewResponse]:
    """查看 Shell 会话输出"""
    # TODO: 实现查看 Shell 逻辑
    return APIResponse.success(ShellViewResponse(console=[]))


@router.post("/{session_id}/file")
async def view_file(
    session_id: str,
    request: FileViewRequest,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[FileViewResponse]:
    """查看文件内容"""
    # TODO: 实现查看文件逻辑
    return APIResponse.success(FileViewResponse())


@router.websocket("/{session_id}/vnc")
async def vnc_websocket(
    websocket: WebSocket,
    session_id: str,
    signature: str = Depends(verify_signature_websocket),
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> None:
    """VNC WebSocket 端点（二进制模式）

    与沙箱环境中的 VNC WebSocket 服务建立连接并双向转发数据
    支持通过签名 URL 进行认证，带有签名验证
    """

    await websocket.accept(subprotocol="binary")
    logger.info(f"接受 WebSocket 连接，会话 {session_id}")

    try:
        # TODO: 获取沙箱环境地址并验证用户
        sandbox_ws_url = f"ws://localhost:5901"

        logger.info(f"连接到 VNC WebSocket: {sandbox_ws_url}")

        # 连接到沙箱 WebSocket
        async with websockets.connect(sandbox_ws_url) as sandbox_ws:
            logger.info(f"已连接到 VNC WebSocket: {sandbox_ws_url}")
            # 创建两个任务来双向转发数据

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

            # 并发运行两个转发任务
            forward_task1 = asyncio.create_task(forward_to_sandbox())
            forward_task2 = asyncio.create_task(forward_from_sandbox())

            # 等待任一任务完成（意味着连接已关闭）
            done, pending = await asyncio.wait(
                [forward_task1, forward_task2], return_when=asyncio.FIRST_COMPLETED
            )

            logger.info("WebSocket 连接关闭")

            # 取消挂起的任务
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
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[List[dict]]:
    """获取会话文件列表"""
    # TODO: 实现获取会话文件列表逻辑
    return APIResponse.success([])


@router.post("/{session_id}/vnc/signed-url", response_model=APIResponse[SignedUrlResponse])
async def create_vnc_signed_url(
    session_id: str,
    request_data: AccessTokenRequest,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[SignedUrlResponse]:
    """为 VNC WebSocket 访问生成签名 URL

    此端点创建一个签名 URL，允许临时访问特定会话的 VNC
    WebSocket，无需认证头。
    """

    # 验证过期时间（最大 15 分钟）
    expire_minutes = request_data.expire_minutes
    if expire_minutes > 15:
        expire_minutes = 15

    # TODO: 检查会话是否存在并属于用户
    # TODO: 创建签名 URL

    signed_url = f"/api/v1/sessions/{session_id}/vnc?signature=temp_signature"

    logger.info(f"为用户 {current_user.get('id')}，会话 {session_id} 创建 VNC 访问签名 URL")

    return APIResponse.success(
        SignedUrlResponse(signed_url=signed_url, expires_in=expire_minutes * 60)
    )


@router.post("/{session_id}/share", response_model=APIResponse[ShareSessionResponse])
async def share_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[ShareSessionResponse]:
    """分享会话，使其可公开访问"""
    # TODO: 实现分享会话逻辑
    return APIResponse.success(ShareSessionResponse(session_id=session_id, is_shared=True))


@router.get("/{session_id}/share/files")
async def get_shared_session_files(
    session_id: str,
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[List[dict]]:
    """获取共享会话的文件"""
    # TODO: 实现获取共享会话文件逻辑
    return APIResponse.success([])


@router.delete("/{session_id}/share", response_model=APIResponse[ShareSessionResponse])
async def unshare_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[ShareSessionResponse]:
    """取消分享会话，使其变为私有"""
    # TODO: 实现取消分享会话逻辑
    return APIResponse.success(ShareSessionResponse(session_id=session_id, is_shared=False))


@router.get("/shared/{session_id}", response_model=APIResponse[SharedSessionResponse])
async def get_shared_session(
    session_id: str,
    agent_service: AgentDomainService = Depends(get_agent_domain_service),
) -> APIResponse[SharedSessionResponse]:
    """无需认证获取共享会话"""
    # TODO: 实现获取共享会话逻辑
    return APIResponse.success(
        SharedSessionResponse(
            session_id=session_id,
            title="Shared Session",
            status="completed",
            events=[],
            is_shared=True,
        )
    )
