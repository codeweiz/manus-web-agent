"""文件路由"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from manus_web_agent.application.errors.exceptions import NotFoundError, UnauthorizedError
from manus_web_agent.application.services.file_service import FileService
from manus_web_agent.interfaces.dependencies import (
    get_current_user,
    get_file_service,
    get_optional_current_user,
    verify_signature,
)
from manus_web_agent.interfaces.schemas.base import APIResponse
from manus_web_agent.interfaces.schemas.file import FileInfoResponse
from manus_web_agent.interfaces.schemas.resource import AccessTokenRequest, SignedUrlResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", response_model=APIResponse[FileInfoResponse])
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> APIResponse[FileInfoResponse]:
    """上传文件"""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空",
        )

    # 读取文件内容
    content = await file.read()

    # 上传文件
    file_info = await file_service.upload_file(
        file_data=content,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        user_id=current_user.get("id"),
    )

    # 添加签名 URL
    await file_service.enrich_with_file_url(file_info)

    return APIResponse.success(
        FileInfoResponse(
            file_id=file_info.file_id,
            filename=file_info.filename,
            content_type=file_info.content_type,
            size=file_info.size,
            url=file_info.url,
            created_at=int(file_info.created_at.timestamp())
            if file_info.created_at
            else None,
        )
    )


@router.get("/{file_id}")
async def download_file_with_signature(
    file_id: str,
    signature: str = Depends(verify_signature),
    file_service: FileService = Depends(get_file_service),
) -> StreamingResponse:
    """下载文件（需签名）"""
    # 验证签名时会检查 URL 是否有效
    file_data, file_info = await file_service.download_file(file_id, user_id=None)

    return StreamingResponse(
        iter([file_data]),
        media_type=file_info.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_info.filename}"},
    )


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> StreamingResponse:
    """下载文件（需登录）"""
    file_data, file_info = await file_service.download_file(
        file_id, user_id=current_user.get("id")
    )

    return StreamingResponse(
        iter([file_data]),
        media_type=file_info.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_info.filename}"},
    )


@router.delete("/{file_id}", response_model=APIResponse[None])
async def delete_file(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> APIResponse[None]:
    """删除文件"""
    success = await file_service.delete_file(file_id, user_id=current_user.get("id"))
    if not success:
        raise NotFoundError("文件不存在")
    return APIResponse.success(msg="文件已删除")


@router.get("/{file_id}/info", response_model=APIResponse[FileInfoResponse])
async def get_file_info(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> APIResponse[FileInfoResponse]:
    """获取文件信息"""
    file_info = await file_service.get_file_info(
        file_id, user_id=current_user.get("id")
    )
    if not file_info:
        raise NotFoundError("文件不存在")

    # 添加签名 URL
    await file_service.enrich_with_file_url(file_info)

    return APIResponse.success(
        await FileInfoResponse.from_file_info(file_info, signed_url=file_info.url)
    )


@router.post("/{file_id}/signed-url", response_model=APIResponse[SignedUrlResponse])
async def create_file_signed_url(
    file_id: str,
    request_data: AccessTokenRequest,
    current_user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> APIResponse[SignedUrlResponse]:
    """创建文件下载签名 URL"""
    # 验证过期时间（最大 15 分钟）
    expire_minutes = request_data.expire_minutes
    if expire_minutes > 15:
        expire_minutes = 15

    # 检查文件是否存在
    file_info = await file_service.get_file_info(
        file_id, user_id=current_user.get("id")
    )
    if not file_info:
        raise NotFoundError("文件不存在")

    # 创建签名 URL
    signed_url = await file_service.create_signed_url(file_id, expire_minutes)

    logger.info(
        f"为用户 {current_user.get('id')}，文件 {file_id} 创建签名 URL"
    )

    return APIResponse.success(
        SignedUrlResponse(
            signed_url=signed_url,
            expires_in=expire_minutes * 60,
        )
    )
