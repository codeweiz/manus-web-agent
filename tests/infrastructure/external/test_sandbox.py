"""Docker Sandbox 测试 - 使用真实 Docker 连接

运行前需要:
    1. Docker 服务运行
    2. 配置沙箱镜像 (在 .config.toml 中):
        [sandbox]
        image = "your-sandbox-image"
        name_prefix = "test-sandbox"

运行测试:
    python -m pytest tests/infrastructure/external/test_sandbox.py -v

注意: 这些测试会创建真实的 Docker 容器
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest

from manus_web_agent.infrastructure.external.sandbox.docker_sandbox import DockerSandbox


# 检查 Docker 是否可用
def is_docker_available():
    """检查 Docker 是否可用"""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


DOCKER_AVAILABLE = is_docker_available()


@pytest.fixture(scope="module")
def sandbox_config():
    """检查沙箱配置"""
    from manus_web_agent.core.toml_config import TOML_CONFIG
    config = TOML_CONFIG.sandbox_config

    if not config.image:
        pytest.skip("沙箱镜像未配置 (sandbox.image)")

    return config


@pytest.mark.asyncio
class TestDockerSandbox:
    """Docker 沙箱功能测试"""

    async def test_docker_connection(self):
        """测试 Docker 连接"""
        if not DOCKER_AVAILABLE:
            pytest.skip("Docker 不可用")

        import docker
        client = docker.from_env()
        info = client.info()

        assert "ServerVersion" in info, "应该能获取 Docker 版本"
        print(f"  Docker 版本: {info['ServerVersion']}")
        print(f"✓ Docker 连接测试通过")

    async def test_create_sandbox(self, sandbox_config):
        """测试创建沙箱"""
        if not DOCKER_AVAILABLE:
            pytest.skip("Docker 不可用")

        # 创建沙箱
        sandbox = await DockerSandbox.create()

        assert sandbox is not None, "应该创建沙箱"
        assert sandbox.id is not None, "沙箱应该有 ID"
        assert sandbox.ip is not None, "沙箱应该有 IP"

        print(f"  沙箱 ID: {sandbox.id}")
        print(f"  沙箱 IP: {sandbox.ip}")
        print(f"✓ 创建沙箱测试通过")

        # 清理
        await sandbox.destroy()

    async def test_sandbox_properties(self, sandbox_config):
        """测试沙箱属性"""
        if not DOCKER_AVAILABLE:
            pytest.skip("Docker 不可用")

        sandbox = await DockerSandbox.create()

        try:
            # 检查属性
            assert sandbox.id, "应该有 id"
            assert sandbox.cdp_url, "应该有 cdp_url"
            assert sandbox.vnc_url, "应该有 vnc_url"

            print(f"  CDP URL: {sandbox.cdp_url}")
            print(f"  VNC URL: {sandbox.vnc_url}")
            print(f"✓ 沙箱属性测试通过")
        finally:
            await sandbox.destroy()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
