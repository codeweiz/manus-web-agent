import logging
from functools import lru_cache
from typing import Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.websockets import WebSocket

from manus_web_agent.application.services.agent_service import AgentService
from manus_web_agent.application.services.auth_service import AuthService
from manus_web_agent.application.services.email_service import EmailService
from manus_web_agent.application.services.file_service import FileService
from manus_web_agent.application.services.token_service import TokenService
from manus_web_agent.core.toml_config import TOML_CONFIG
from manus_web_agent.domain.models.user import User, UserRole
from manus_web_agent.domain.services.agent_domain_service import AgentDomainService
from manus_web_agent.infrastructure.external.cache import get_cache
from manus_web_agent.infrastructure.external.file import get_file_storage
from manus_web_agent.infrastructure.external.llm.openai_llm import OpenAILLM
from manus_web_agent.infrastructure.external.sandbox.docker_sandbox import DockerSandbox
from manus_web_agent.infrastructure.external.search import get_search_engine
from manus_web_agent.infrastructure.external.task.redis_task import RedisStreamTask
from manus_web_agent.infrastructure.repositories.file_mcp_repository import (
    FileMCPRepository,
)
from manus_web_agent.infrastructure.repositories.mongo_agent_repository import (
    MongoAgentRepository,
)
from manus_web_agent.infrastructure.repositories.mongo_session_repository import (
    MongoSessionRepository,
)
from manus_web_agent.infrastructure.repositories.user_repository import (
    MongoUserRepository,
)
from manus_web_agent.infrastructure.utils.llm_json_parser import LLMJsonParser

logger = logging.getLogger(__name__)

# Security scheme - Bearer Token only
security_bearer = HTTPBearer(auto_error=False)


@lru_cache()
def get_token_service() -> TokenService:
    """获取 TokenService 实例"""
    return TokenService()


@lru_cache()
def get_email_service() -> Optional[EmailService]:
    """获取 EmailService 实例"""
    try:
        cache = get_cache()
        return EmailService(cache=cache)
    except Exception as e:
        logger.warning(f"邮件服务初始化失败: {e}")
        return None


@lru_cache()
def get_auth_service() -> AuthService:
    """
    获取 AuthService 实例

    使用 lru_cache 实现单例模式
    """
    logger.info("创建 AuthService 实例")

    user_repository = MongoUserRepository()
    token_service = get_token_service()
    email_service = get_email_service()

    return AuthService(
        user_repository=user_repository,
        token_service=token_service,
        email_service=email_service,
    )


@lru_cache()
def get_agent_domain_service() -> AgentDomainService:
    """
    获取 AgentDomainService 实例及所有必需的依赖

    使用 lru_cache 实现单例模式
    """
    logger.info("创建 AgentDomainService 实例")

    # 创建所有依赖
    llm = OpenAILLM()
    agent_repository = MongoAgentRepository()
    session_repository = MongoSessionRepository()
    sandbox_cls = DockerSandbox
    task_cls = RedisStreamTask
    json_parser = LLMJsonParser(llm=llm)
    file_storage = get_file_storage()
    mcp_repository = FileMCPRepository()
    search_engine = get_search_engine()

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
        search_engine=search_engine,
    )


@lru_cache()
def get_agent_service() -> AgentService:
    """获取 AgentService 实例"""
    logger.info("创建 AgentService 实例")

    agent_domain_service = get_agent_domain_service()
    token_service = get_token_service()

    return AgentService(
        agent_domain_service=agent_domain_service,
        token_service=token_service,
    )


@lru_cache()
def get_file_service() -> FileService:
    """获取 FileService 实例"""
    logger.info("创建 FileService 实例")

    file_storage = get_file_storage()
    token_service = get_token_service()

    return FileService(
        file_storage=file_storage,
        token_service=token_service,
    )


async def get_current_user(
    bearer_credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """
    获取当前认证用户（必需）

    此依赖使用 Bearer Token 强制执行认证
    """
    # 获取认证提供者配置
    auth_provider = getattr(TOML_CONFIG, "auth_provider", "none")

    # 如果 auth_provider 是 'none'，返回匿名用户
    if auth_provider == "none":
        return {
            "id": "anonymous",
            "fullname": "anonymous",
            "email": "anonymous@localhost",
            "role": UserRole.USER.value,
        }

    # 检查是否提供了 bearer token
    if not bearer_credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证",
        )

    try:
        # 验证 bearer token
        user = await auth_service.verify_token(bearer_credentials.credentials)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效令牌",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账户已停用",
            )

        return {
            "id": user.id,
            "fullname": user.fullname,
            "email": user.email,
            "role": user.role.value,
        }

    except Exception as e:
        logger.warning(f"认证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
        )


async def get_optional_current_user(
    bearer_credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[dict]:
    """
    获取当前认证用户（可选）

    此依赖允许认证和匿名访问
    """
    # 获取认证提供者配置
    auth_provider = getattr(TOML_CONFIG, "auth_provider", "none")

    # 如果 auth_provider 是 'none'，返回匿名用户
    if auth_provider == "none":
        return {
            "id": "anonymous",
            "fullname": "anonymous",
            "email": "anonymous@localhost",
            "role": UserRole.USER.value,
        }

    # 如果没有提供 bearer token，返回 None
    if not bearer_credentials:
        return None

    try:
        # 尝试验证 bearer token
        user = await auth_service.verify_token(bearer_credentials.credentials)

        if user and user.is_active:
            return {
                "id": user.id,
                "fullname": user.fullname,
                "email": user.email,
                "role": user.role.value,
            }

    except Exception as e:
        logger.warning(f"可选认证失败: {e}")

    return None


async def verify_signature(
    request: Request,
    signature: Optional[str] = Query(None),
) -> str:
    """验证签名 URL 访问的签名"""
    token_service = get_token_service()

    if not signature:
        logger.error(f"缺少签名: {request.url}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少签名",
        )

    if not token_service.verify_signed_url(str(request.url)):
        logger.error(f"无效签名: {request.url}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效签名",
        )

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
            detail="缺少签名",
        )
    return signature
