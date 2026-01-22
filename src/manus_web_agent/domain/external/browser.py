from typing import Protocol, Optional

from manus_web_agent.domain.models.tool_result import ToolResult


class Browser(Protocol):
    """浏览器服务网关接口"""

    async def view_page(self) -> ToolResult:
        """查看页面"""
        pass

    async def navigate(self, url: str) -> ToolResult:
        """导航到 URL"""
        pass

    async def restart(self, url: str) -> ToolResult:
        """重启浏览器并导航到 URL"""
        pass

    async def click(
            self,
            index: Optional[int] = None,
            coordinate_x: Optional[float] = None,
            coordinate_y: Optional[float] = None
    ) -> ToolResult:
        """点击元素"""
        pass

    async def input(
            self,
            text: str,
            press_enter: bool,
            index: Optional[int] = None,
            coordinate_x: Optional[float] = None,
            coordinate_y: Optional[float] = None
    ):
        """输入文本"""
        pass

    async def move_mouse(
            self,
            coordinate_x: float,
            coordinate_y: float
    ) -> ToolResult:
        """移动鼠标"""
        pass

    async def press_key(self, key: str) -> ToolResult:
        """按下键"""
        pass

    async def select_option(
            self,
            index: int,
            option: int
    ) -> ToolResult:
        """选择选项"""
        pass

    async def scroll_up(self, to_top: Optional[bool] = None) -> ToolResult:
        """滚动到顶部"""
        pass

    async def scroll_down(self, to_bottom: Optional[bool] = None) -> ToolResult:
        """滚动到底部"""
        pass

    async def screen_shot(self, full_page: Optional[bool] = False) -> bytes:
        """截图"""

    async def console_exec(self, javascript: str) -> ToolResult:
        """执行 JavaScript"""
        pass

    async def console_view(self, max_lines: Optional[int] = None) -> ToolResult:
        """查看控制台"""
        pass
