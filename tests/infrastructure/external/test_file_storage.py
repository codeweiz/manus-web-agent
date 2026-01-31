"""GridFS 文件存储测试 - 使用真实 MongoDB 连接

运行前需要启动 MongoDB:
    docker run -d -p 27017:27017 --name mongodb mongo:latest

运行测试:
    python -m pytest tests/infrastructure/external/test_file_storage.py -v
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime

# 确保能导入项目代码
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest

from manus_web_agent.infrastructure.external.file.gridfsfile import GridFSFileStorage
from manus_web_agent.infrastructure.storage.mongodb import MongoDB


@pytest.fixture(scope="module")
async def file_storage():
    """提供 GridFSFileStorage 实例"""
    # 初始化 MongoDB
    mongodb = MongoDB()
    await mongodb.initialize()

    storage = GridFSFileStorage()

    yield storage

    # 清理
    await mongodb.shutdown()


@pytest.fixture
def test_file_data():
    """生成测试文件数据"""
    return {
        "content": f"Test file content {uuid.uuid4().hex}\nLine 2\nLine 3".encode("utf-8"),
        "filename": f"test_file_{uuid.uuid4().hex[:8]}.txt",
        "content_type": "text/plain",
    }


@pytest.mark.asyncio
class TestGridFSFileStorage:
    """GridFS 文件存储功能测试"""

    async def test_upload_file(self, file_storage, test_file_data):
        """测试文件上传"""
        file_info = await file_storage.upload_file(
            file_data=test_file_data["content"],
            filename=test_file_data["filename"],
            content_type=test_file_data["content_type"],
            user_id="test_user",
        )

        assert file_info is not None, "上传应该返回 FileInfo"
        assert file_info.file_id is not None, "应该有 file_id"
        assert file_info.filename == test_file_data["filename"], "文件名应该匹配"
        assert file_info.size == len(test_file_data["content"]), "文件大小应该匹配"
        assert file_info.content_type == test_file_data["content_type"], "内容类型应该匹配"

        print(f"✓ 上传测试通过: {file_info.file_id}")

        # 清理
        await file_storage.delete_file(file_info.file_id)

    async def test_upload_and_download(self, file_storage, test_file_data):
        """测试上传和下载"""
        # 上传
        file_info = await file_storage.upload_file(
            file_data=test_file_data["content"],
            filename=test_file_data["filename"],
            content_type=test_file_data["content_type"],
        )

        # 下载
        downloaded_data, downloaded_info = await file_storage.download_file(
            file_id=file_info.file_id
        )

        assert downloaded_data == test_file_data["content"], "下载内容应该与上传一致"
        assert downloaded_info.filename == test_file_data["filename"], "文件名应该匹配"
        assert downloaded_info.size == len(test_file_data["content"]), "大小应该匹配"

        print(f"✓ 上传下载测试通过: {file_info.file_id}")

        # 清理
        await file_storage.delete_file(file_info.file_id)

    async def test_get_file_info(self, file_storage, test_file_data):
        """测试获取文件信息"""
        # 上传
        file_info = await file_storage.upload_file(
            file_data=test_file_data["content"],
            filename=test_file_data["filename"],
            content_type=test_file_data["content_type"],
        )

        # 获取信息
        info = await file_storage.get_file_info(file_info.file_id)

        assert info is not None, "应该能获取到文件信息"
        assert info.file_id == file_info.file_id, "file_id 应该匹配"
        assert info.filename == test_file_data["filename"], "文件名应该匹配"
        assert info.size == len(test_file_data["content"]), "大小应该匹配"

        print(f"✓ 获取信息测试通过: {file_info.file_id}")

        # 清理
        await file_storage.delete_file(file_info.file_id)

    async def test_file_exists(self, file_storage, test_file_data):
        """测试文件存在检查"""
        # 上传前不存在
        exists = await file_storage.file_exists("000000000000000000000000")
        assert exists is False, "不存在的文件应该返回 False"

        # 上传
        file_info = await file_storage.upload_file(
            file_data=test_file_data["content"],
            filename=test_file_data["filename"],
        )

        # 上传后存在
        exists = await file_storage.file_exists(file_info.file_id)
        assert exists is True, "存在的文件应该返回 True"

        print(f"✓ 存在检查测试通过: {file_info.file_id}")

        # 清理
        await file_storage.delete_file(file_info.file_id)

    async def test_delete_file(self, file_storage, test_file_data):
        """测试删除文件"""
        # 上传
        file_info = await file_storage.upload_file(
            file_data=test_file_data["content"],
            filename=test_file_data["filename"],
        )

        # 确认存在
        assert await file_storage.file_exists(file_info.file_id) is True

        # 删除
        result = await file_storage.delete_file(file_info.file_id)
        assert result is True, "删除应该返回 True"

        # 确认不存在
        assert await file_storage.file_exists(file_info.file_id) is False

        # 删除不存在的文件应该返回 False
        result = await file_storage.delete_file(file_info.file_id)
        assert result is False, "删除不存在的文件应该返回 False"

        print(f"✓ 删除测试通过")

    async def test_download_nonexistent_file(self, file_storage):
        """测试下载不存在的文件"""
        with pytest.raises(FileNotFoundError):
            await file_storage.download_file("000000000000000000000000")

        print(f"✓ 下载不存在文件测试通过")

    async def test_large_file(self, file_storage):
        """测试大文件上传下载"""
        # 生成 1MB 的测试数据
        large_content = b"x" * (1024 * 1024)
        filename = f"large_file_{uuid.uuid4().hex[:8]}.bin"

        # 上传
        file_info = await file_storage.upload_file(
            file_data=large_content,
            filename=filename,
            content_type="application/octet-stream",
        )

        assert file_info.size == len(large_content), "大文件大小应该匹配"

        # 下载
        downloaded_data, downloaded_info = await file_storage.download_file(
            file_id=file_info.file_id
        )

        assert len(downloaded_data) == len(large_content), "下载大小应该匹配"
        assert downloaded_data == large_content, "大文件内容应该一致"

        print(f"✓ 大文件测试通过: {len(large_content)} bytes")

        # 清理
        await file_storage.delete_file(file_info.file_id)

    async def test_binary_file(self, file_storage):
        """测试二进制文件"""
        # 生成随机二进制数据
        binary_content = bytes([i % 256 for i in range(1024)])
        filename = f"binary_{uuid.uuid4().hex[:8]}.bin"

        # 上传
        file_info = await file_storage.upload_file(
            file_data=binary_content,
            filename=filename,
            content_type="application/octet-stream",
        )

        # 下载
        downloaded_data, _ = await file_storage.download_file(file_info.file_id)

        assert downloaded_data == binary_content, "二进制内容应该完全一致"

        print(f"✓ 二进制文件测试通过")

        # 清理
        await file_storage.delete_file(file_info.file_id)

    async def test_special_filename(self, file_storage):
        """测试特殊文件名"""
        test_cases = [
            "中文文件名.txt",
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file.multiple.dots.txt",
        ]

        for filename in test_cases:
            content = f"Content for {filename}".encode("utf-8")

            file_info = await file_storage.upload_file(
                file_data=content,
                filename=filename,
            )

            assert file_info.filename == filename, f"文件名应该匹配: {filename}"

            # 清理
            await file_storage.delete_file(file_info.file_id)

        print(f"✓ 特殊文件名测试通过: {len(test_cases)} 个")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
