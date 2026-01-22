from typing import Optional

from manus_web_agent.domain.external.browser import Browser
from manus_web_agent.domain.models.tool_result import ToolResult
from manus_web_agent.domain.services.tools.base import BaseTool, tool


class BrowserTool(BaseTool):
    """浏览器工具"""

    name: str = "browser"

    def __init__(self, browser: Browser):
        super().__init__()
        self.browser = browser

    @tool(
        name="browser_view",
        description="View content of the current browser page. Use for checking the latest state of previously opened pages.",
        parameters={},
        required=[],
    )
    async def browser_view(self) -> ToolResult:
        """查看页面"""
        return await self.browser.view_page()

    @tool(
        name="browser_navigate",
        description="Navigate to a URL. Use for opening a new page or navigating to a different page.",
        parameters={"url": {"type": "string", "description": "URL to navigate to. Must be a valid URL."}},
        required=["url"],
    )
    async def browser_navigate(self, url: str) -> ToolResult:
        """导航到 URL"""
        return await self.browser.navigate(url)

    @tool(
        name="browser_restart",
        description="Restart the browser and navigate to a URL. Use for clearing the browser state and starting fresh.",
        parameters={"url": {"type": "string", "description": "URL to navigate to. Must be a valid URL."}},
        required=["url"],
    )
    async def browser_restart(self, url: str) -> ToolResult:
        """重启浏览器并导航到 URL"""
        return await self.browser.restart(url)

    @tool(
        name="browser_click",
        description="Click an element on the page. Use for interacting with buttons, links, and other clickable elements.",
        parameters={
            "index": {
                "type": "integer",
                "description": "Optional. Index of the element to click."
            },
            "coordinate_x": {
                "type": "number",
                "description": "Optional. X coordinate of the element to click."
            },
            "coordinate_y": {
                "type": "number",
                "description": "Optional. Y coordinate of the element to click."
            }
        },
        required=[],
    )
    async def browser_click(
            self,
            index: Optional[int] = None,
            coordinate_x: Optional[float] = None,
            coordinate_y: Optional[float] = None
    ) -> ToolResult:
        """点击元素"""
        return await self.browser.click(index, coordinate_x, coordinate_y)

    @tool(
        name="browser_input",
        description="Input text into an element on the page. Use for filling in text fields.",
        parameters={
            "text": {
                "type": "string",
                "description": "Text to input."
            },
            "press_enter": {
                "type": "boolean",
                "description": "Whether to press enter after inputting the text."
            },
            "index": {
                "type": "integer",
                "description": "Optional. Index of the element to input text into."
            },
            "coordinate_x": {
                "type": "number",
                "description": "Optional. X coordinate of the element to input text into."
            },
            "coordinate_y": {
                "type": "number",
                "description": "Optional. Y coordinate of the element to input text into."
            }
        },
        required=["text", "press_enter"],
    )
    async def browser_input(
            self,
            text: str,
            press_enter: bool,
            index: Optional[int] = None,
            coordinate_x: Optional[float] = None,
            coordinate_y: Optional[float] = None
    ) -> ToolResult:
        """输入文本"""
        return await self.browser.input(text, press_enter, index, coordinate_x, coordinate_y)

    @tool(
        name="browser_move_mouse",
        description="Move the mouse to a specific coordinate on the page. Use for hovering over elements.",
        parameters={
            "coordinate_x": {
                "type": "number",
                "description": "X coordinate to move the mouse to."
            },
            "coordinate_y": {
                "type": "number",
                "description": "Y coordinate to move the mouse to."
            }
        },
        required=["coordinate_x", "coordinate_y"],
    )
    async def browser_move_mouse(
            self,
            coordinate_x: float,
            coordinate_y: float
    ) -> ToolResult:
        """移动鼠标"""
        return await self.browser.move_mouse(coordinate_x, coordinate_y)

    @tool(
        name="browser_press_key",
        description="Press a key on the keyboard. Use for interacting with elements that require keyboard input.",
        parameters={"key": {"type": "string", "description": "Key to press."}},
        required=["key"],
    )
    async def browser_press_key(self, key: str) -> ToolResult:
        """按下键"""
        return await self.browser.press_key(key)

    @tool(
        name="browser_select_option",
        description="When there is a dropdown menu on the page, Select an option from a dropdown menu. Use for interacting with dropdown menus.",
        parameters={
            "index": {
                "type": "integer",
                "description": "Index of the dropdown menu to select from."
            },
            "option": {
                "type": "integer",
                "description": "Index of the option to select."
            }
        },
        required=["index", "option"],
    )
    async def browser_select_option(
            self,
            index: int,
            option: int
    ) -> ToolResult:
        """选择选项"""
        return await self.browser.select_option(index, option)

    @tool(
        name="browser_scroll_up",
        description="Scroll up. Use for scrolling up the page.",
        parameters={
            "to_top": {
                "type": "boolean",
                "description": "Whether to scroll to the top of the page."
            }
        },
        required=[],
    )
    async def browser_scroll_up(self, to_top: Optional[bool] = None) -> ToolResult:
        """滚动到顶部"""
        return await self.browser.scroll_up(to_top)

    @tool(
        name="browser_scroll_down",
        description="Scroll down. Use for scrolling down the page.",
        parameters={
            "to_bottom": {
                "type": "boolean",
                "description": "Whether to scroll to the bottom of the page."
            }
        },
        required=[],
    )
    async def browser_scroll_down(self, to_bottom: Optional[bool] = None) -> ToolResult:
        """滚动到底部"""
        return await self.browser.scroll_down(to_bottom)

    @tool(
        name="browser_console_exec",
        description="Execute JavaScript in the browser console. Use for interacting with the page using JavaScript.",
        parameters={"javascript": {"type": "string", "description": "JavaScript to execute."}},
        required=["javascript"],
    )
    async def browser_console_exec(self, javascript: str) -> ToolResult:
        """执行 JavaScript"""
        return await self.browser.console_exec(javascript)

    @tool(
        name="browser_console_view",
        description="View the browser console. Use for checking the latest state of previously opened pages.",
        parameters={
            "max_lines": {
                "type": "integer",
                "description": "Maximum number of lines to return."
            }
        },
        required=[],
    )
    async def browser_console_view(self, max_lines: Optional[int] = None) -> ToolResult:
        """查看控制台"""
        return await self.browser.console_view(max_lines)
