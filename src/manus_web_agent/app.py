"""FastAPI 应用入口"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from manus_web_agent.core.toml_config import TOML_CONFIG
from manus_web_agent.infrastructure.models.documents import (
    AgentDocument,
    SessionDocument,
    UserDocument,
)
from manus_web_agent.infrastructure.storage.mongodb import get_mongodb
from manus_web_agent.interfaces.api.routes import router as api_router
from manus_web_agent.interfaces.errors.exception_handlers import register_exception_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("正在初始化应用...")

    # 注册 Beanie 文档模型
    mongodb = get_mongodb()
    mongodb.register_models([UserDocument, AgentDocument, SessionDocument])

    # 初始化 MongoDB
    await mongodb.initialize()

    logger.info("应用初始化完成")

    yield

    # 关闭时清理
    logger.info("正在关闭应用...")

    # 关闭 AgentDomainService
    from manus_web_agent.interfaces.dependencies import get_agent_domain_service

    agent_domain_service = get_agent_domain_service()
    await agent_domain_service.shutdown()

    # 关闭 MongoDB 连接
    await mongodb.shutdown()

    logger.info("应用已关闭")


def create_application() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    app = FastAPI(
        title="Manus Web Agent API",
        description="A tribute to Manus, dedicated to build the best web agents",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应该限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册异常处理器
    register_exception_handlers(app)

    # 注册 API 路由
    app.include_router(api_router, prefix="/api/v1")

    return app


# 创建应用实例
app = create_application()


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/")
async def root():
    """根路径重定向到 API 文档"""
    return {
        "message": "Manus Web Agent API",
        "docs": "/docs",
        "health": "/health",
    }
