from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """文件信息"""

    file_id: Optional[str] = Field(default=None, description="文件 ID")

    filename: Optional[str] = Field(default=None, description="文件名")

    file_path: Optional[str] = Field(default=None, description="文件路径")

    content_type: Optional[str] = Field(default=None, description="文件类型")

    size: Optional[int] = Field(default=None, description="文件大小")

    upload_date: Optional[datetime] = Field(default=None, description="上传日期")

    metadata: Optional[dict] = Field(default=None, description="元数据")

    user_id: Optional[str] = Field(default=None, description="用户 ID")

    file_url: Optional[str] = Field(default=None, description="文件 URL")
