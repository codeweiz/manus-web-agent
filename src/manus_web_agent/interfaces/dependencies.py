import logging
from functools import lru_cache
from typing import Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.websockets import WebSocket

from manus_web_agent.domain.services.agent_domain_service import AgentDomainService
from manus_web_agent.infrastructure.external.llm.openai_llm import OpenAILLM
from manus_web_agent.infrastructure.external.sandbox.docker_sandbox import DockerSandbox
from manus_web_agent.infrastructure.storage.mongodb import get_mongodb
from manus_web_agent.infrastructure.storage.redis import get_redis

logger = logging.getLogger(__name__)

# Security scheme - Bearer Token only
security_bearer = HTTPBearer(auto_error=False)


@lru_cache()
def get_agent_domain_service() -> AgentDomainService:
    """
    获取 AgentDomainService 实例及所有必需的依赖

    此函数创建并返回带有所有必要依赖的 AgentDomainService 实例。
    使用 lru_cache 实现单例模式。
    """
    logger.info("创建 AgentDomainService 实例")

    # 创建所有依赖
    llm = OpenAILLM()
    agent_repository = None  # TODO: 实现 MongoAgentRepository
    session_repository = None  # TODO: 实现 MongoSessionRepository
    sandbox_cls = DockerSandbox
    task_cls = None  # TODO: 实现 RedisStreamTask
    json_parser = None  # TODO: 实现 LLMJsonParser
    file_storage = None  # TODO: 实现 GridFSFileStorage
    mcp_repository = None  # TODO: 实现 FileMCPRepository

    # 创建 AgentDomainService 实例
    return AgentDomainService(
        llm=llm,
        agent_repository=agent_repository,
        session_repository=session_repository,
        sandbox_cls=sandbox_cls,
        task_cls=task_cls,
        json_parser=json_parser,
        file_storage=file_storage,
        mcp_repository=mcp_repository,
    )


async def get_current_user(
    bearer_credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> dict:
    """
    获取当前认证用户（必需）

    此依赖使用 Bearer Token 强制执行认证。
    如果认证失败，则抛出 HTTPException。
    """
    # 如果没有提供 bearer token，返回匿名用户
    if not bearer_credentials:
        return {"id": "anonymous", "fullname": "anonymous", "email": "anonymous@localhost"}

    try:
        # TODO: 实现 token 验证
        # 这里简化处理，实际应该验证 JWT token
        return {"id": "user_id", "fullname": "User", "email": "user@example.com"}
    except Exception as e:
        logger.warning(f"认证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败"
        )


async def get_optional_current_user(
    bearer_credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> Optional[dict]:
    """
    获取当前认证用户（可选）

    此依赖允许认证和匿名访问。
    如果认证失败或未提供，则返回 None。

    使用 Bearer Token 认证。
    """
    # 如果没有提供 bearer token，返回 None
    if not bearer_credentials:
        return None

    try:
        # TODO: 实现 token 验证
        return {"id": "user_id", "fullname": "User", "email": "user@example.com"}
    except Exception as e:
        logger.warning(f"可选认证失败: {e}")

    return None


async def verify_signature(
    request: Request,
    signature: Optional[str] = Query(None),
) -> str:
    """
    验证签名 URL 访问的签名

    此依赖验证请求 URL 中的签名参数。
    如果签名缺失或无效，则抛出 HTTPException。

    设计用于普通 HTTP 端点和 WebSocket 端点。
    对于 WebSocket 连接，异常将在连接建立之前抛出，
    防止无效连接被建立。

    :param request: 传入的请求
    :param signature: 签名查询参数
    :return: 验证通过的签名字符串

    :raises HTTPException: 如果签名缺失或无效（状态码 401）
    """
    if not signature:
        logger.error(f"缺少签名: {request.url}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少签名"
        )

    # TODO: 实现签名验证逻辑
    # if not token_service.verify_signed_url(str(request.url)):
    #     logger.error(f"无效签名: {request.url}")
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="无效签名"
    #     )

    return signature


async def verify_signature_websocket(
    websocket: WebSocket,
    signature: Optional[str] = Query(None),
) -> str:
    """WebSocket 签名验证"""
    if not signature:
        logger.error(f"WebSocket 缺少签名")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少签名"
        )
    return signature
