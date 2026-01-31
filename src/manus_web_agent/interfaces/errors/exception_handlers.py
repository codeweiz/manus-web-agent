"""全局异常处理器"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from manus_web_agent.application.errors.exceptions import AppException
from manus_web_agent.interfaces.schemas.base import APIResponse

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理应用层异常"""
    logger.warning(f"应用异常: {exc.message}, 路径: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse.error(code=exc.code, msg=exc.message).model_dump(),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """处理 HTTP 异常"""
    logger.warning(f"HTTP 异常: {exc.detail}, 路径: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse.error(
            code=exc.status_code, msg=str(exc.detail)
        ).model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """处理验证异常"""
    errors = exc.errors()
    message = "; ".join(
        [f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in errors]
    )
    logger.warning(f"验证异常: {message}, 路径: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse.error(code=400, msg=message).model_dump(),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理通用异常"""
    logger.exception(f"未处理异常: {exc}, 路径: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse.error(
            code=500, msg="服务器内部错误"
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """注册所有异常处理器"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    logger.info("异常处理器已注册")
