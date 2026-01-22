from typing import Protocol, BinaryIO, Optional, Dict, Any, Tuple

from manus_web_agent.domain.models.file import FileInfo


class FileStorage(Protocol):
    """文件存储服务网关接口"""

    async def upload_file(
            self,
            file_data: BinaryIO,
            filename: str,
            user_id: str,
            content_type: Optional[str] = None,
            meta_data: Optional[Dict[str, Any]] = None
    ) -> FileInfo:
        """上传文件
        :param file_data: 文件数据
        :param filename: 文件名
        :param user_id: 用户 ID
        :param content_type: 文件类型
        :param meta_data: 元数据
        :return: 文件信息
        """
        pass

    async def download_file(self, file_id: str, user_id: str) -> Tuple[BinaryIO, FileInfo]:
        """下载文件
        :param file_id: 文件 ID
        :param user_id: 用户 ID
        :return: 文件数据和文件信息
        """
        pass

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """删除文件
        :param file_id: 文件 ID
        :param user_id: 用户 ID
        :return: 是否成功
        """
        pass

    async def get_file_info(self, file_id: str, user_id: Optional[str]) -> FileInfo:
        """获取文件信息
        :param file_id: 文件 ID
        :param user_id: 用户 ID
        :return: 文件信息
        """
        pass
