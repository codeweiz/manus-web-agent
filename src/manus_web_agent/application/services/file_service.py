"""文件服务"""

from typing import Optional, Tuple

from manus_web_agent.application.services.token_service import TokenService
from manus_web_agent.domain.external.file import FileStorage
from manus_web_agent.domain.models.file import FileInfo


class FileService:
    """文件服务，处理文件上传、下载和签名 URL"""

    def __init__(self, file_storage: FileStorage, token_service: TokenService):
        self._file_storage = file_storage
        self._token_service = token_service

    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        user_id: str
    ) -> FileInfo:
        """上传文件

        :param file_data: 文件数据
        :param filename: 文件名
        :param content_type: 内容类型
        :param user_id: 用户 ID
        :return: 文件信息
        """
        return await self._file_storage.upload_file(file_data, filename, content_type, user_id)

    async def download_file(self, file_id: str, user_id: str) -> Tuple[bytes, FileInfo]:
        """下载文件

        :param file_id: 文件 ID
        :param user_id: 用户 ID
        :return: 文件数据和信息
        """
        return await self._file_storage.download_file(file_id, user_id)

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """删除文件

        :param file_id: 文件 ID
        :param user_id: 用户 ID
        :return: 是否成功
        """
        return await self._file_storage.delete_file(file_id, user_id)

    async def get_file_info(self, file_id: str, user_id: str) -> Optional[FileInfo]:
        """获取文件信息

        :param file_id: 文件 ID
        :param user_id: 用户 ID
        :return: 文件信息
        """
        return await self._file_storage.get_file_info(file_id, user_id)

    async def enrich_with_file_url(self, file_info: FileInfo, expire_minutes: int = 15) -> FileInfo:
        """为文件信息添加签名 URL

        :param file_info: 文件信息
        :param expire_minutes: 过期时间（分钟）
        :return: 添加了 URL 的文件信息
        """
        base_url = f"/api/v1/files/{file_info.file_id}"
        file_info.url = self._token_service.create_signed_url(base_url, expire_minutes)
        return file_info

    async def create_signed_url(self, file_id: str, expire_minutes: int = 15) -> str:
        """为文件创建签名 URL

        :param file_id: 文件 ID
        :param expire_minutes: 过期时间（分钟）
        :return: 签名 URL
        """
        base_url = f"/api/v1/files/{file_id}"
        return self._token_service.create_signed_url(base_url, expire_minutes)
