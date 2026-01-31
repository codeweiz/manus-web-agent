from fastapi import APIRouter

from manus_web_agent.interfaces.api import auth_routes, file_routes, session_routes


def create_api_router() -> APIRouter:
    """创建并配置主 API 路由器"""
    api_router = APIRouter()

    # 包含所有子路由器
    api_router.include_router(session_routes.router)
    api_router.include_router(file_routes.router)
    api_router.include_router(auth_routes.router)

    return api_router


# 创建主路由器实例
router = create_api_router()
