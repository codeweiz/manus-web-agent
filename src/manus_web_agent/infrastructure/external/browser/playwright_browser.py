import asyncio
import logging
from typing import Dict, Any, Optional, List

from markdownify import markdownify
from playwright.async_api import async_playwright, Browser, Page

from manus_web_agent.domain.external.browser import Browser as BrowserProtocol
from manus_web_agent.domain.models.tool_result import ToolResult
from manus_web_agent.infrastructure.external.llm.openai_llm import OpenAILLM

logger = logging.getLogger(__name__)


class PlaywrightBrowser(BrowserProtocol):
    """Playwright 浏览器实现"""

    def __init__(self, cdp_url: str):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.llm = OpenAILLM()
        self.cdp_url = cdp_url

    async def initialize(self) -> bool:
        """初始化并确保资源可用"""
        # 添加重试逻辑
        max_retries = 5
        retry_delay = 1  # 初始等待 1 秒

        for attempt in range(max_retries):
            try:
                self.playwright = await async_playwright().start()
                # 连接到现有的 Chrome 实例
                self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)
                # 获取所有上下文
                contexts = self.browser.contexts
                if contexts and len(contexts[0].pages) == 1:
                    # 检查是否是初始页面（通过 URL）
                    page = contexts[0].pages[0]
                    page_url = await page.evaluate("window.location.href")
                    if (
                        page_url == "about:blank" or
                        page_url == "chrome://newtab/" or
                        page_url == "chrome://new-tab-page/" or
                        not page_url
                    ):
                        # 只有在是初始页面且只有一个标签页时才使用它
                        self.page = page
                    else:
                        # 不是初始页面，创建新页面
                        self.page = await contexts[0].new_page()
                else:
                    # 其他情况下创建新页面
                    context = contexts[0] if contexts else await self.browser.new_context()
                    self.page = await context.new_page()
                return True
            except Exception as e:
                # 清理失败的资源
                await self.cleanup()

                # 如果达到最大重试次数，返回错误
                if attempt == max_retries - 1:
                    logger.error(f"初始化失败（重试 {max_retries} 次）: {e}")
                    return False

                # 否则增加等待时间（指数退避策略）
                retry_delay = min(retry_delay * 2, 10)  # 最大等待 10 秒
                logger.warning(f"初始化失败，将在 {retry_delay} 秒后重试: {e}")
                await asyncio.sleep(retry_delay)

    async def cleanup(self) -> None:
        """清理 Playwright 资源，先关闭所有标签页，再关闭浏览器"""
        try:
            # 如果浏览器存在，先关闭所有标签页
            if self.browser:
                # 获取所有上下文
                contexts = self.browser.contexts
                if contexts:
                    for context in contexts:
                        # 获取上下文中的所有页面
                        pages = context.pages
                        # 关闭所有页面
                        for page in pages:
                            # 避免多次关闭 self.page
                            if page != self.page or (self.page and not self.page.is_closed()):
                                await page.close()

            # 确保当前页面已关闭（如果存在且未关闭）
            if self.page and not self.page.is_closed():
                await self.page.close()

            # 关闭浏览器
            if self.browser:
                await self.browser.close()

            # 停止 playwright
            if self.playwright:
                await self.playwright.stop()

        except Exception as e:
            logger.error(f"清理资源时出错: {e}")
        finally:
            # 重置引用
            self.page = None
            self.browser = None
            self.playwright = None

    async def _ensure_browser(self) -> None:
        """确保浏览器已启动"""
        if not self.browser or not self.page:
            if not await self.initialize():
                raise Exception("无法初始化浏览器资源")

    async def _ensure_page(self) -> None:
        """确保页面已创建并更新到当前活动标签页（最右边的标签页）"""
        await self._ensure_browser()
        if not self.page:
            self.page = await self.browser.new_page()
        else:
            # 获取所有上下文
            contexts = self.browser.contexts
            if contexts:
                # 获取当前上下文中的所有页面
                current_context = contexts[0]
                pages = current_context.pages

                if pages:
                    # 获取最右边的标签页（通常是最近打开的页面）
                    rightmost_page = pages[-1]

                    # 如果当前页面不是最右边的标签页，则更新
                    if self.page != rightmost_page:
                        # 更新到最右边的标签页
                        self.page = rightmost_page

    async def wait_for_page_load(self, timeout: int = 15) -> bool:
        """等待页面加载完成，最多等待指定的超时时间

        :param timeout: 最大等待时间（秒），默认 15 秒
        :return: 是否成功等待页面加载完成
        """
        await self._ensure_page()

        start_time = asyncio.get_event_loop().time()
        check_interval = 5  # 每 5 秒检查一次

        while asyncio.get_event_loop().time() - start_time < timeout:
            # 检查页面是否已完全加载
            is_loaded = await self.page.evaluate("""() => {
                return document.readyState === 'complete';
            }""")

            if is_loaded:
                return True

            # 等待一段时间后再检查
            await asyncio.sleep(check_interval)

        # 超时，页面加载未完成
        return False

    async def _extract_content(self) -> str:
        """从当前页面提取内容"""

        # 执行 JavaScript 获取视口中的元素
        visible_content = await self.page.evaluate("""() => {
            const visibleElements = [];
            const viewportHeight = window.innerHeight;
            const viewportWidth = window.innerWidth;

            // 获取所有可能相关的元素
            const elements = document.querySelectorAll('body *');

            for (const element of elements) {
                // 检查元素是否在视口中且可见
                const rect = element.getBoundingClientRect();

                // 元素必须有尺寸
                if (rect.width === 0 || rect.height === 0) continue;

                // 元素必须在视口内
                if (
                    rect.bottom < 0 ||
                    rect.top > viewportHeight ||
                    rect.right < 0 ||
                    rect.left > viewportWidth
                ) continue;

                // 检查元素是否可见（未被 CSS 隐藏）
                const style = window.getComputedStyle(element);
                if (
                    style.display === 'none' ||
                    style.visibility === 'hidden' ||
                    style.opacity === '0'
                ) continue;

                // 如果是文本节点或有意义的元素，添加到结果中
                if (
                    element.innerText ||
                    element.tagName === 'IMG' ||
                    element.tagName === 'INPUT' ||
                    element.tagName === 'BUTTON'
                ) {
                    visibleElements.push(element.outerHTML);
                }
            }

            // 构建包含这些可见元素的 HTML
            return '<div>' + visibleElements.join('') + '</div>';
        }""")

        # 转换为 Markdown
        markdown_content = markdownify(visible_content)

        max_content_length = min(50000, len(markdown_content))
        response = await self.llm.ask([{
            "role": "system",
            "content": "你是一个专业的网页信息提取助手。请从当前页面内容中提取所有信息并转换为 Markdown 格式。"
        },
            {
                "role": "user",
                "content": markdown_content[:max_content_length]
            }
        ])

        return response.get("content", "")

    async def view_page(self) -> ToolResult:
        """查看当前页面视口中的可见元素并转换为 Markdown 格式"""
        await self._ensure_page()

        # 等待页面完全加载，最多等待 15 秒
        await self.wait_for_page_load()

        # 首先更新交互元素缓存
        interactive_elements = await self._extract_interactive_elements()

        return ToolResult(
            success=True,
            data={
                "interactive_elements": interactive_elements,
                "content": await self._extract_content(),
            }
        )

    async def _extract_interactive_elements(self) -> List[str]:
        """返回页面上可见的交互元素列表，格式为 index:<tag>text</tag>"""
        await self._ensure_page()

        # 清除当前页面的缓存以确保我们总是获取最新的元素列表
        self.page.interactive_elements_cache = []

        # 执行 JavaScript 获取视口中的交互元素
        interactive_elements = await self.page.evaluate("""() => {
            const interactiveElements = [];
            const viewportHeight = window.innerHeight;
            const viewportWidth = window.innerWidth;

            // 获取所有可能相关的交互元素
            const elements = document.querySelectorAll('button, a, input, textarea, select, [role="button"], [tabindex]:not([tabindex="-1"])');

            let validElementIndex = 0; // 用于生成连续的索引

            for (let i = 0; i < elements.length; i++) {
                const element = elements[i];
                // 检查元素是否在视口中且可见
                const rect = element.getBoundingClientRect();

                // 元素必须有尺寸
                if (rect.width === 0 || rect.height === 0) continue;

                // 元素必须在视口内
                if (
                    rect.bottom < 0 ||
                    rect.top > viewportHeight ||
                    rect.right < 0 ||
                    rect.left > viewportWidth
                ) continue;

                // 检查元素是否可见（未被 CSS 隐藏）
                const style = window.getComputedStyle(element);
                if (
                    style.display === 'none' ||
                    style.visibility === 'hidden' ||
                    style.opacity === '0'
                ) continue;

                // 获取元素类型和文本
                let tagName = element.tagName.toLowerCase();
                let text = '';

                if (element.value && ['input', 'textarea', 'select'].includes(tagName)) {
                    text = element.value;

                    // 为输入元素添加标签和占位符信息
                    if (tagName === 'input') {
                        // 获取关联的标签文本
                        let labelText = '';
                        if (element.id) {
                            const label = document.querySelector(`label[for="${element.id}"]`);
                            if (label) {
                                labelText = label.innerText.trim();
                            }
                        }

                        // 查找父级或兄弟标签
                        if (!labelText) {
                            const parentLabel = element.closest('label');
                            if (parentLabel) {
                                labelText = parentLabel.innerText.trim().replace(element.value, '').trim();
                            }
                        }

                        // 添加标签信息
                        if (labelText) {
                            text = `[Label: ${labelText}] ${text}`;
                        }

                        // 添加占位符信息
                        if (element.placeholder) {
                            text = `${text} [Placeholder: ${element.placeholder}]`;
                        }
                    }
                } else if (element.innerText) {
                    text = element.innerText.trim().replace(/\\s+/g, ' ');
                } else if (element.alt) { // 图片按钮
                    text = element.alt;
                } else if (element.title) { // 有 title 的元素
                    text = element.title;
                } else if (element.placeholder) { // 占位符文本
                    text = `[Placeholder: ${element.placeholder}]`;
                } else if (element.type) { // 输入类型
                    text = `[${element.type}]`;

                    // 为无文本的输入元素添加标签和占位符信息
                    if (tagName === 'input') {
                        // 获取关联的标签文本
                        let labelText = '';
                        if (element.id) {
                            const label = document.querySelector(`label[for="${element.id}"]`);
                            if (label) {
                                labelText = label.innerText.trim();
                            }
                        }

                        // 查找父级或兄弟标签
                        if (!labelText) {
                            const parentLabel = element.closest('label');
                            if (parentLabel) {
                                labelText = parentLabel.innerText.trim();
                            }
                        }

                        // 添加标签信息
                        if (labelText) {
                            text = `[Label: ${labelText}] ${text}`;
                        }

                        // 添加占位符信息
                        if (element.placeholder) {
                            text = `${text} [Placeholder: ${element.placeholder}]`;
                        }
                    }
                } else {
                    text = '[No text]';
                }

                // 文本长度最大限制，保持清晰
                if (text.length > 100) {
                    text = text.substring(0, 97) + '...';
                }

                // 只给符合条件的元素添加 data-manus-id 属性
                element.setAttribute('data-manus-id', `manus-element-${validElementIndex}`);

                // 构建选择器 - 只使用 data-manus-id
                const selector = `[data-manus-id="manus-element-${validElementIndex}"]`;

                // 添加元素信息到数组
                interactiveElements.push({
                    index: validElementIndex,  // 使用连续索引
                    tag: tagName,
                    text: text,
                    selector: selector
                });

                validElementIndex++; // 递增有效元素计数器
            }

            return interactiveElements;
        }""")

        # 更新缓存
        self.page.interactive_elements_cache = interactive_elements

        # 以指定格式格式化元素信息
        formatted_elements = []
        for el in interactive_elements:
            formatted_elements.append(f"{el['index']}:<{el['tag']}>{el['text']}</{el['tag']}>")

        return formatted_elements

    async def navigate(self, url: str, timeout: Optional[int] = 15000) -> ToolResult:
        """导航到指定 URL

        :param url: 要导航到的 URL
        :param timeout: 导航超时（毫秒），默认 60 秒
        """
        await self._ensure_page()
        try:
            # 清除缓存，因为页面即将改变
            self.page.interactive_elements_cache = []
            try:
                await self.page.goto(url, timeout=timeout)
            except Exception as e:
                logger.warning(f"导航到 {url} 失败: {str(e)}")
            return ToolResult(
                success=True,
                data={
                    "interactive_elements": await self._extract_interactive_elements(),
                }
            )
        except Exception as e:
            return ToolResult(success=False, message=f"导航到 {url} 失败: {str(e)}")

    async def restart(self, url: str) -> ToolResult:
        """重启浏览器并导航到指定 URL"""
        await self.cleanup()
        return await self.navigate(url)

    async def _get_element_by_index(self, index: int) -> Optional[Any]:
        """使用 data-manus-id 选择器通过索引获取元素

        :param index: 元素索引
        :return: 找到的元素，如果未找到则返回 None
        """
        # 检查是否有缓存的元素
        if not hasattr(self.page, 'interactive_elements_cache') or not self.page.interactive_elements_cache or index >= len(
                self.page.interactive_elements_cache):
            return None

        # 使用 data-manus-id 选择器
        selector = f'[data-manus-id="manus-element-{index}"]'
        return await self.page.query_selector(selector)

    async def click(
            self,
            index: Optional[int] = None,
            coordinate_x: Optional[float] = None,
            coordinate_y: Optional[float] = None
    ) -> ToolResult:
        """点击元素"""
        await self._ensure_page()
        if coordinate_x is not None and coordinate_y is not None:
            await self.page.mouse.click(coordinate_x, coordinate_y)
        elif index is not None:
            try:
                element = await self._get_element_by_index(index)
                if not element:
                    return ToolResult(success=False, message=f"找不到索引为 {index} 的交互元素")

                # 检查元素是否可见
                is_visible = await self.page.evaluate("""(element) => {
                    if (!element) return false;
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    return !(
                        rect.width === 0 ||
                        rect.height === 0 ||
                        style.display === 'none' ||
                        style.visibility === 'hidden' ||
                        style.opacity === '0'
                    );
                }""", element)

                if not is_visible:
                    # 尝试滚动到元素位置
                    await self.page.evaluate("""(element) => {
                        if (element) {
                            element.scrollIntoView({behavior: 'smooth', block: 'center'});
                        }
                    }""", element)
                    # 等待元素可见
                    await asyncio.sleep(1)

                # 尝试点击元素
                await element.click(timeout=5000)
            except Exception as e:
                return ToolResult(success=False, message=f"点击元素失败: {str(e)}")
        return ToolResult(success=True)

    async def input(
            self,
            text: str,
            press_enter: bool,
            index: Optional[int] = None,
            coordinate_x: Optional[float] = None,
            coordinate_y: Optional[float] = None
    ) -> ToolResult:
        """输入文本"""
        await self._ensure_page()
        if coordinate_x is not None and coordinate_y is not None:
            await self.page.mouse.click(coordinate_x, coordinate_y)
            await self.page.keyboard.type(text)
        elif index is not None:
            try:
                element = await self._get_element_by_index(index)
                if not element:
                    return ToolResult(success=False, message=f"找不到索引为 {index} 的交互元素")

                # 尝试使用 fill() 方法，但捕获可能的错误
                try:
                    await element.fill("")
                    await element.type(text)
                except Exception as e:
                    # 如果 fill() 失败，直接使用 type() 方法
                    await element.click()
                    await self.page.keyboard.type(text)
            except Exception as e:
                return ToolResult(success=False, message=f"输入文本失败: {str(e)}")

        if press_enter:
            await self.page.keyboard.press("Enter")
        return ToolResult(success=True)

    async def move_mouse(
            self,
            coordinate_x: float,
            coordinate_y: float
    ) -> ToolResult:
        """移动鼠标"""
        await self._ensure_page()
        await self.page.mouse.move(coordinate_x, coordinate_y)
        return ToolResult(success=True)

    async def press_key(self, key: str) -> ToolResult:
        """模拟按键"""
        await self._ensure_page()
        await self.page.keyboard.press(key)
        return ToolResult(success=True)

    async def select_option(
            self,
            index: int,
            option: int
    ) -> ToolResult:
        """选择下拉选项"""
        await self._ensure_page()
        try:
            element = await self._get_element_by_index(index)
            if not element:
                return ToolResult(success=False, message=f"找不到索引为 {index} 的选择器元素")

            # 尝试选择选项
            await element.select_option(index=option)
            return ToolResult(success=True)
        except Exception as e:
            return ToolResult(success=False, message=f"选择选项失败: {str(e)}")

    async def scroll_up(
            self,
            to_top: Optional[bool] = None
    ) -> ToolResult:
        """向上滚动"""
        await self._ensure_page()
        if to_top:
            await self.page.evaluate("window.scrollTo(0, 0)")
        else:
            await self.page.evaluate("window.scrollBy(0, -window.innerHeight)")
        return ToolResult(success=True)

    async def scroll_down(
            self,
            to_bottom: Optional[bool] = None
    ) -> ToolResult:
        """向下滚动"""
        await self._ensure_page()
        if to_bottom:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        else:
            await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
        return ToolResult(success=True)

    async def screenshot(
            self,
            full_page: Optional[bool] = False
    ) -> bytes:
        """截取当前页面截图

        :param full_page: 是否截取整个页面或仅视口
        :return: PNG 截图数据
        """
        await self._ensure_page()

        # 配置截图选项
        screenshot_options = {
            "full_page": full_page,
            "type": "png"
        }

        # 直接返回字节数据
        return await self.page.screenshot(**screenshot_options)

    async def console_exec(self, javascript: str) -> ToolResult:
        """执行 JavaScript 代码"""
        await self._ensure_page()
        result = await self.page.evaluate(javascript)
        return ToolResult(success=True, data={"result": result})

    async def console_view(self, max_lines: Optional[int] = None) -> ToolResult:
        """查看控制台输出"""
        await self._ensure_page()
        logs = await self.page.evaluate("""() => {
            return window.console.logs || [];
        }""")
        if max_lines is not None:
            logs = logs[-max_lines:]
        return ToolResult(success=True, data={"logs": logs})
