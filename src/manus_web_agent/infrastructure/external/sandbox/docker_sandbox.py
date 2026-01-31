import asyncio
import io
import logging
import socket
import uuid
from typing import BinaryIO, Optional

import docker
import httpx
from async_lru import alru_cache

from manus_web_agent.core.toml_config import TOML_CONFIG
from manus_web_agent.domain.external.browser import Browser
from manus_web_agent.domain.external.sandbox import Sandbox
from manus_web_agent.domain.models.tool_result import ToolResult
from manus_web_agent.infrastructure.external.browser.playwright_browser import PlaywrightBrowser

logger = logging.getLogger(__name__)


class DockerSandbox(Sandbox):
    """Docker 沙箱实现"""

    def __init__(self, ip: str = None, container_name: str = None):
        """初始化 Docker 沙箱和 API 交互客户端"""
        self.client = httpx.AsyncClient(timeout=600)
        self.ip = ip
        self.base_url = f"http://{self.ip}:8080"
        self._vnc_url = f"ws://{self.ip}:5901"
        self._cdp_url = f"http://{self.ip}:9222"
        self._container_name = container_name

    @property
    def id(self) -> str:
        """沙箱 ID"""
        if not self._container_name:
            return "dev-sandbox"
        return self._container_name

    @property
    def cdp_url(self) -> str:
        """CDP URL"""
        return self._cdp_url

    @property
    def vnc_url(self) -> str:
        """VNC URL"""
        return self._vnc_url

    @staticmethod
    def _get_container_ip(container) -> str:
        """从容器的网络设置中获取 IP 地址

        :param container: Docker 容器实例
        :return: 容器 IP 地址
        """
        # 获取容器网络设置
        network_settings = container.attrs['NetworkSettings']
        ip_address = network_settings['IPAddress']

        # 如果默认网络没有 IP，尝试从其他网络获取
        if not ip_address and 'Networks' in network_settings:
            networks = network_settings['Networks']
            # 尝试从第一个可用网络获取 IP
            for network_name, network_config in networks.items():
                if 'IPAddress' in network_config and network_config['IPAddress']:
                    ip_address = network_config['IPAddress']
                    break

        return ip_address

    @staticmethod
    def _create_task() -> 'DockerSandbox':
        """创建新的 Docker 沙箱（静态方法）

        :return: DockerSandbox 实例
        """
        # 使用配置的默认值
        config = TOML_CONFIG.sandbox_config

        image = config.image
        name_prefix = config.name_prefix
        container_name = f"{name_prefix}-{str(uuid.uuid4())[:8]}"

        try:
            # 创建 Docker 客户端
            docker_client = docker.from_env()

            # 准备容器配置
            container_config = {
                "image": image,
                "name": container_name,
                "detach": True,
                "remove": True,
                "environment": {
                    "SERVICE_TIMEOUT_MINUTES": config.ttl_minutes,
                    "CHROME_ARGS": config.chrome_args,
                    "HTTPS_PROXY": config.https_proxy,
                    "HTTP_PROXY": config.http_proxy,
                    "NO_PROXY": config.no_proxy
                }
            }

            # 如果配置了网络，添加到容器配置
            if config.network:
                container_config["network"] = config.network

            # 创建容器
            container = docker_client.containers.run(**container_config)

            # 获取容器 IP 地址
            container.reload()  # 刷新容器信息
            ip_address = DockerSandbox._get_container_ip(container)

            # 创建并返回 DockerSandbox 实例
            return DockerSandbox(
                ip=ip_address,
                container_name=container_name
            )

        except Exception as e:
            raise Exception(f"创建 Docker 沙箱失败: {str(e)}")

    async def ensure_sandbox(self) -> None:
        """确保沙箱已就绪，通过检查所有服务是否都在运行"""
        max_retries = 30  # 最大重试次数
        retry_interval = 2  # 重试间隔（秒）

        for attempt in range(max_retries):
            try:
                response = await self.client.get(f"{self.base_url}/api/v1/supervisor/status")
                response.raise_for_status()

                # 解析响应为 ToolResult
                tool_result = ToolResult(**response.json())

                if not tool_result.success:
                    logger.warning(f"Supervisor 状态检查失败: {tool_result.message}")
                    await asyncio.sleep(retry_interval)
                    continue

                services = tool_result.data or []
                if not services:
                    logger.warning("Supervisor 状态中没有找到服务")
                    await asyncio.sleep(retry_interval)
                    continue

                # 检查所有服务是否都在运行
                all_running = True
                non_running_services = []

                for service in services:
                    service_name = service.get("name", "unknown")
                    state_name = service.get("statename", "")

                    if state_name != "RUNNING":
                        all_running = False
                        non_running_services.append(f"{service_name}({state_name})")

                if all_running:
                    logger.info(f"所有 {len(services)} 个服务都在运行 - 沙箱已就绪")
                    return  # 成功 - 所有服务都在运行
                else:
                    logger.info(f"等待服务启动... 未运行的服务: {', '.join(non_running_services)} (尝试 {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_interval)

            except Exception as e:
                logger.warning(f"检查 supervisor 状态失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                await asyncio.sleep(retry_interval)

        # 如果到达这里，说明已经耗尽了所有重试次数
        error_message = f"沙箱服务在 {max_retries} 次尝试后未能启动 ({max_retries * retry_interval} 秒)"
        logger.error(error_message)
        # 销毁失败的沙箱并抛出异常
        await self.destroy()
        raise RuntimeError(error_message)

    async def exec_command(self, session_id: str, exec_dir: str, command: str) -> ToolResult:
        """执行命令"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/shell/exec",
            json={
                "id": session_id,
                "exec_dir": exec_dir,
                "command": command
            }
        )
        return ToolResult(**response.json())

    async def view_shell(self, session_id: str, console: bool = False) -> ToolResult:
        """查看 Shell"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/shell/view",
            json={
                "id": session_id,
                "console": console
            }
        )
        return ToolResult(**response.json())

    async def wait_for_process(self, session_id: str, seconds: Optional[int] = None) -> ToolResult:
        """等待进程"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/shell/wait",
            json={
                "id": session_id,
                "seconds": seconds
            }
        )
        return ToolResult(**response.json())

    async def write_to_process(self, session_id: str, input_text: str, press_enter: bool = True) -> ToolResult:
        """写入到进程"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/shell/write",
            json={
                "id": session_id,
                "input": input_text,
                "press_enter": press_enter
            }
        )
        return ToolResult(**response.json())

    async def kill_process(self, session_id: str) -> ToolResult:
        """杀死进程"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/shell/kill",
            json={"id": session_id}
        )
        return ToolResult(**response.json())

    async def file_write(
            self,
            file: str,
            content: str,
            append: bool = False,
            leading_newline: bool = False,
            trailing_newline: bool = False,
            sudo: bool = False
    ) -> ToolResult:
        """写入内容到文件"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/file/write",
            json={
                "file": file,
                "content": content,
                "append": append,
                "leading_newline": leading_newline,
                "trailing_newline": trailing_newline,
                "sudo": sudo
            }
        )
        return ToolResult(**response.json())

    async def file_read(
            self,
            file: str,
            start_line: Optional[int] = None,
            end_line: Optional[int] = None,
            sudo: bool = False
    ) -> ToolResult:
        """读取文件内容"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/file/read",
            json={
                "file": file,
                "start_line": start_line,
                "end_line": end_line,
                "sudo": sudo
            }
        )
        return ToolResult(**response.json())

    async def file_exists(self, path: str) -> ToolResult:
        """检查文件是否存在"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/file/exists",
            json={"path": path}
        )
        return ToolResult(**response.json())

    async def file_delete(self, path: str) -> ToolResult:
        """删除文件"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/file/delete",
            json={"path": path}
        )
        return ToolResult(**response.json())

    async def file_list(self, path: str) -> ToolResult:
        """列出目录内容"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/file/list",
            json={"path": path}
        )
        return ToolResult(**response.json())

    async def file_replaces(self, file: str, old_str: str, new_str: str, sudo: bool = False) -> ToolResult:
        """替换文件中的字符串"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/file/replace",
            json={
                "file": file,
                "old_str": old_str,
                "new_str": new_str,
                "sudo": sudo
            }
        )
        return ToolResult(**response.json())

    async def file_search(self, file: str, regex: str, sudo: bool = False) -> ToolResult:
        """搜索文件内容"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/file/search",
            json={
                "file": file,
                "regex": regex,
                "sudo": sudo
            }
        )
        return ToolResult(**response.json())

    async def file_find(self, path: str, glob_pattern: str) -> ToolResult:
        """通过文件名模式查找文件"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/file/find",
            json={
                "path": path,
                "glob": glob_pattern
            }
        )
        return ToolResult(**response.json())

    async def file_upload(self, file_data: BinaryIO, path: str, filename: Optional[str] = None) -> ToolResult:
        """上传文件到沙箱"""
        # 准备上传的表单数据
        files = {"file": (filename or "upload", file_data, "application/octet-stream")}
        data = {"path": path}

        response = await self.client.post(
            f"{self.base_url}/api/v1/file/upload",
            files=files,
            data=data
        )
        return ToolResult(**response.json())

    async def file_download(self, path: str) -> BinaryIO:
        """从沙箱下载文件"""
        import tempfile
        import shutil

        response = await self.client.get(
            f"{self.base_url}/api/v1/file/download",
            params={"path": path},
            timeout=300  # 增加下载超时时间
        )
        response.raise_for_status()

        # 对于小文件直接返回内存流
        content_length = len(response.content)
        if content_length < 10 * 1024 * 1024:  # 小于 10MB 使用内存流
            return io.BytesIO(response.content)

        # 大文件使用临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(response.content)
        temp_file.seek(0)
        return temp_file

    @staticmethod
    @alru_cache(maxsize=128, typed=True)
    async def _resolve_hostname_to_ip(hostname: str) -> Optional[str]:
        """将主机名解析为 IP 地址

        :param hostname: 要解析的主机名
        :return: 解析后的 IP 地址，如果解析失败则返回 None

        注意:
            此方法使用 LRU 缓存，最大缓存条目数为 128。
            缓存有助于减少对相同主机名的重复 DNS 查询。
        """
        try:
            # 首先检查主机名是否已经是 IP 地址格式
            try:
                socket.inet_pton(socket.AF_INET, hostname)
                # 如果成功解析，说明是 IPv4 地址格式，直接返回
                return hostname
            except OSError:
                # 不是有效的 IP 地址格式，继续 DNS 解析
                pass

            # 使用 socket.getaddrinfo 进行 DNS 解析
            addr_info = socket.getaddrinfo(hostname, None, family=socket.AF_INET)
            # 返回找到的第一个 IPv4 地址
            if addr_info and len(addr_info) > 0:
                return addr_info[0][4][0]  # 返回 (family, type, proto, canonname, sockaddr) 中的 sockaddr[0]，即 IP 地址
            return None
        except Exception as e:
            # 记录错误并在失败时返回 None
            logger.error(f"解析主机名 {hostname} 失败: {str(e)}")
            return None

    async def destroy(self) -> bool:
        """销毁 Docker 沙箱"""
        try:
            if self.client:
                await self.client.aclose()
            if self._container_name:
                docker_client = docker.from_env()
                docker_client.containers.get(self._container_name).remove(force=True)
            return True
        except Exception as e:
            logger.error(f"销毁 Docker 沙箱失败: {str(e)}")
            return False

    async def get_browser(self) -> Browser:
        """获取浏览器实例

        :return: 返回使用沙箱的 CDP URL 配置的 PlaywrightBrowser 实例
        """
        return PlaywrightBrowser(self.cdp_url)

    @classmethod
    async def create(cls) -> Sandbox:
        """创建新的沙箱实例

        :return: 新的沙箱实例
        """
        config = TOML_CONFIG.sandbox_config

        if config.address:
            # Chrome CDP 需要 IP 地址
            ip = await cls._resolve_hostname_to_ip(config.address)
            return DockerSandbox(ip=ip)

        return await asyncio.to_thread(DockerSandbox._create_task)

    @classmethod
    @alru_cache(maxsize=128, typed=True)
    async def get(cls, id: str) -> Sandbox:
        """通过 ID 获取沙箱

        :param id: 沙箱 ID
        :return: 沙箱实例
        """
        config = TOML_CONFIG.sandbox_config
        if config.address:
            ip = await cls._resolve_hostname_to_ip(config.address)
            return DockerSandbox(ip=ip, container_name=id)

        docker_client = docker.from_env()
        container = docker_client.containers.get(id)
        container.reload()

        ip_address = cls._get_container_ip(container)
        logger.info(f"IP 地址: {ip_address}")
        return DockerSandbox(ip=ip_address, container_name=id)
