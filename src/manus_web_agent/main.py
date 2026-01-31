"""应用入口点"""

import logging
import os

import uvicorn

from manus_web_agent.infrastructure.logging import setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    """启动应用"""
    # 设置日志
    setup_logging()

    # 获取配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"

    logger.info(f"启动 Manus Web Agent API 服务器: {host}:{port}")

    # 启动 uvicorn 服务器
    uvicorn.run(
        "manus_web_agent.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
