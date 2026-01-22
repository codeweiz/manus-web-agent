from typing import Protocol, Optional, BinaryIO

from manus_web_agent.domain.external.browser import Browser
from manus_web_agent.domain.models.tool_result import ToolResult


class Sandbox(Protocol):
    """沙箱服务网关接口"""

    async def ensure_sandbox(self) -> None:
        """确保沙箱存在"""
        pass

    async def exec_command(
            self,
            session_id: str,
            exec_dir: str,
            command: str,
    ) -> ToolResult:
        """执行命令
        :param session_id: 会话 ID
        :param exec_dir: 执行目录
        :param command: 命令
        :return: 执行结果
        """
        pass

    async def view_shell(self, session_id: str, console: bool = False) -> ToolResult:
        """查看 Shell
        :param session_id: 会话 ID
        :param console: 是否返回控制台结果
        :return: 查看结果
        """
        pass

    async def wait_for_process(self, session_id: str, seconds: Optional[int] = None) -> ToolResult:
        """等待进程
        :param session_id: 会话 ID
        :param seconds: 等待秒数
        :return: 等待结果
        """
        pass

    async def write_to_process(
            self,
            session_id: str,
            input_text: str,
            press_enter: bool = True,
    ) -> ToolResult:
        """写入到进程
        :param session_id: 会话 ID
        :param input_text: 输入文本
        :param press_enter: 是否按下回车
        :return: 写入结果
        """
        pass

    async def kill_process(self, session_id: str) -> ToolResult:
        """杀死进程
        :param session_id: 会话 ID
        :return: 杀死结果
        """
        pass

    async def file_write(
            self,
            file: str,
            content: str,
            append: bool = False,
            leading_newline: bool = False,
            trailing_newline: bool = False,
            sudo: bool = False
    ) -> ToolResult:
        """写入内容到文件
        :param file: 文件路径
        :param content: 文件内容
        :param append: 是否追加
        :param leading_newline: 是否在开头添加换行符
        :param trailing_newline: 是否在结尾添加换行符
        :param sudo: 是否使用 sudo
        :return: 写入结果
        """
        pass

    async def file_read(
            self,
            file: str,
            start_line: Optional[int] = None,
            end_line: Optional[int] = None,
            sudo: bool = False
    ) -> ToolResult:
        """读取文件内容
        :param file: 文件路径
        :param start_line: 起始行号
        :param end_line: 结束行号
        :param sudo: 是否使用 sudo
        :return: 读取结果
        """
        pass

    async def file_exists(self, path: str) -> ToolResult:
        """检查文件是否存在
        :param path: 文件路径
        :return: 检查结果
        """
        pass

    async def file_delete(self, path: str) -> ToolResult:
        """删除文件
        :param path: 文件路径
        :return: 删除结果
        """
        pass

    async def file_list(self, path: str) -> ToolResult:
        """列出文件
        :param path: 文件路径
        :return: 文件列表
        """
        pass

    async def file_replaces(self, file: str, old_str: str, new_str: str, sudo: bool = False) -> ToolResult:
        """替换文件内容
        :param file: 文件路径
        :param old_str: 旧字符串
        :param new_str: 新字符串
        :param sudo: 是否使用 sudo
        :return: 替换结果
        """
        pass

    async def file_search(self, file: str, regex: str, sudo: bool = False) -> ToolResult:
        """搜索文件内容
        :param file: 文件路径
        :param regex: 正则表达式
        :param sudo: 是否使用 sudo
        :return: 搜索结果
        """
        pass

    async def file_find(self, path: str, glob_pattern: str) -> ToolResult:
        """查找文件
        :param path: 文件路径
        :param glob_pattern: glob 模式
        :return: 查找结果
        """
        pass

    async def file_upload(self, file_data: BinaryIO, path: str, filename: Optional[str] = None) -> ToolResult:
        """上传文件
        :param file_data: 文件数据
        :param path: 文件路径
        :param filename: 文件名
        :return: 上传结果
        """
        pass

    async def file_download(self, path: str) -> BinaryIO:
        """下载文件
        :param path: 文件路径
        :return: 下载结果
        """
        pass

    async def destroy(self) -> bool:
        """销毁沙箱
        :return: 是否成功
        """
        pass

    async def get_browser(self) -> Browser:
        """获取浏览器
        :return: 浏览器
        """
        pass

    @property
    def id(self) -> str:
        """获取沙箱 ID
        :return: 沙箱 ID
        """
        pass

    @property
    def cdp_url(self) -> str:
        """获取 CDP URL
        :return: CDP URL
        """
        pass

    @property
    def vnc_url(self) -> str:
        """获取 VNC URL
        :return: VNC URL
        """
        pass

    @classmethod
    async def create(cls) -> 'Sandbox':
        """创建沙箱
        :return: 沙箱
        """
        pass

    @classmethod
    async def get(cls, _id: str) -> 'Sandbox':
        """获取沙箱
        :param _id: 沙箱 ID
        :return: 沙箱
        """
        pass
