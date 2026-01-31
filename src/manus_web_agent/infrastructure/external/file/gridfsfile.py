"""GridFS 文件存储实现"""

import logging
from datetime import datetime
from typing import Optional, Tuple

import gridfs
from bson import ObjectId

from manus_web_agent.domain.external.file import FileStorage
from manus_web_agent.domain.models.file import FileInfo
from manus_web_agent.infrastructure.storage.mongodb import get_mongodb

logger = logging.getLogger(__name__)


class GridFSFileStorage(FileStorage):
    """GridFS 文件存储实现"""

    def __init__(self):
        self._mongodb = get_mongodb()

    def _get_fs(self):
        """获取 GridFS 实例"""
        return gridfs.GridFS(self._mongodb.database)

    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> FileInfo:
        """上传文件

        :param file_data: 文件数据
        :param filename: 文件名
        :param content_type: 内容类型
        :param user_id: 用户 ID
        :return: 文件信息
        """
        fs = self._get_fs()

        # 保存文件到 GridFS
        file_id = fs.put(
            file_data,
            filename=filename,
            content_type=content_type or "application/octet-stream",
            user_id=user_id,
            upload_date=datetime.utcnow(),
        )

        file_info = FileInfo(
            file_id=str(file_id),
            filename=filename,
            content_type=content_type,
            size=len(file_data),
            created_at=datetime.utcnow(),
        )

        logger.info(f"上传文件 {filename}，ID: {file_id}")
        return file_info

    async def download_file(
        self, file_id: str, user_id: Optional[str] = None
    ) -> Tuple[bytes, FileInfo]:
        """下载文件

        :param file_id: 文件 ID
        :param user_id: 用户 ID
        :return: 文件数据和信息
        """
        fs = self._get_fs()

        try:
            file_obj = fs.get(ObjectId(file_id))
        except gridfs.NoFile:
            raise FileNotFoundError(f"文件不存在: {file_id}")

        file_info = FileInfo(
            file_id=file_id,
            filename=file_obj.filename,
            content_type=file_obj.content_type,
            size=file_obj.length,
            created_at=file_obj.upload_date,
        )

        logger.debug(f"下载文件 {file_info.filename}，ID: {file_id}")
        return file_obj.read(), file_info

    async def delete_file(self, file_id: str, user_id: Optional[str] = None) -> bool:
        """删除文件

        :param file_id: 文件 ID
        :param user_id: 用户 ID
        :return: 是否成功
        """
        fs = self._get_fs()

        try:
            fs.delete(ObjectId(file_id))
            logger.info(f"删除文件 {file_id}")
            return True
        except gridfs.NoFile:
            logger.warning(f"尝试删除不存在的文件: {file_id}")
            return False

    async def get_file_info(
        self, file_id: str, user_id: Optional[str] = None
    ) -> Optional[FileInfo]:
        """获取文件信息

        :param file_id: 文件 ID
        :param user_id: 用户 ID
        :return: 文件信息
        """
        fs = self._get_fs()

        try:
            file_obj = fs.get(ObjectId(file_id))
            return FileInfo(
                file_id=file_id,
                filename=file_obj.filename,
                content_type=file_obj.content_type,
                size=file_obj.length,
                created_at=file_obj.upload_date,
            )
        except gridfs.NoFile:
            return None

    async def file_exists(self, file_id: str, user_id: Optional[str] = None) -> bool:
        """检查文件是否存在

        :param file_id: 文件 ID
        :param user_id: 用户 ID
        :return: 是否存在
        """
        fs = self._get_fs()
        return fs.exists(ObjectId(file_id))
