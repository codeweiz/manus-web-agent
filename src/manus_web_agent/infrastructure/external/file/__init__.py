"""文件存储模块"""

from manus_web_agent.infrastructure.external.file.gridfsfile import GridFSFileStorage


def get_file_storage():
    """获取文件存储实例"""
    return GridFSFileStorage()


__all__ = ["GridFSFileStorage", "get_file_storage"]
