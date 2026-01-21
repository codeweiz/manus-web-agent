from typing import Optional, List

from pydantic import BaseModel, Field


class FileReadResult(BaseModel):
    """文件读取结果"""

    content: str = Field(..., description="文件内容")

    file: str = Field(..., description="文件路径")


class FileWriteResult(BaseModel):
    """文件写入结果"""

    file: str = Field(..., description="文件路径")

    bytes_written: Optional[int] = Field(default=None, description="写入字节数")


class FileReplaceResult(BaseModel):
    """文件替换结果"""

    file: str = Field(..., description="文件路径")

    replaced_count: int = Field(default=0, description="替换数")


class FileFindResult(BaseModel):
    """文件查找结果"""

    path: str = Field(..., description="查找文件夹路径")

    files: List[str] = Field(default_factory=list, description="找到的文件列表")


class FileUploadResult(BaseModel):
    """文件上传结果"""

    file_path: str = Field(..., description="文件路径")

    file_size: int = Field(..., description="文件大小")

    success: bool = Field(..., description="是否成功")
