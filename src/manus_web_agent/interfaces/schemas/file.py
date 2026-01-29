from typing import Optional

from pydantic import BaseModel, Field

from manus_web_agent.domain.models.file import FileInfo


class FileViewRequest(BaseModel):
    """文件查看请求"""
    file: str = Field(..., description="文件路径")


class FileViewResponse(BaseModel):
    """文件查看响应"""
    content: Optional[str] = Field(default=None, description="文件内容")
    file: Optional[FileInfo] = Field(default=None, description="文件信息")


class FileInfoResponse(BaseModel):
    """文件信息响应"""
    file_id: str = Field(..., description="文件 ID")
    filename: str = Field(..., description="文件名")
    content_type: Optional[str] = Field(default=None, description="内容类型")
    size: Optional[int] = Field(default=None, description="文件大小")
    url: Optional[str] = Field(default=None, description="访问 URL")
    created_at: Optional[int] = Field(default=None, description="创建时间")

    @classmethod
    async def from_file_info(cls, file_info: FileInfo, signed_url: Optional[str] = None) -> "FileInfoResponse":
        """从 FileInfo 创建响应

        :param file_info: 文件信息
        :param signed_url: 签名 URL
        :return: 文件信息响应
        """
        return cls(
            file_id=file_info.file_id,
            filename=file_info.filename,
            content_type=file_info.content_type,
            size=file_info.size,
            url=signed_url,
            created_at=int(file_info.created_at.timestamp()) if file_info.created_at else None
        )
