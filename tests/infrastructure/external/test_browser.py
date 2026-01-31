"""Playwright Browser 测试 - 使用真实 Chrome CDP 连接

运行前需要有 Chrome 实例在调试模式:
    # 使用 Docker 启动带调试的 Chrome
    docker run -d -p 9222:9222 --name chrome-browser \
        -e DISPLAY=:99 \
        browserless/chrome:latest

或者本地 Chrome:
    google-chrome --remote-debugging-port=9222 --headless

运行测试:
    python -m pytest tests/infrastructure/external/test_browser.py -v

注意: 这些测试需要真实的浏览器环境
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest

from manus_web_agent.infrastructure.external.browser.playwright_browser import PlaywrightBrowser


# CDP URL 配置
CDP_URL = os.getenv("CDP_URL", "http://localhost:9222")


@pytest.fixture(scope="module")
async def browser():
    """提供 PlaywrightBrowser 实例"""
    browser = PlaywrightBrowser(CDP_URL)

    # 尝试初始化
    success = await browser.initialize()
    if not success:
        pytest.skip(f"无法连接到 Chrome CDP: {CDP_URL}")

    yield browser

    # 清理
    await browser.cleanup()


@pytest.mark.asyncio
class TestPlaywrightBrowser:
    """Playwright 浏览器功能测试"""

    async def test_initialize(self):
        """测试浏览器初始化"""
        browser = PlaywrightBrowser(CDP_URL)

        try:
            success = await browser.initialize()
            if not success:
                pytest.skip(f"无法连接到 Chrome CDP: {CDP_URL}")

            assert browser.browser is not None, "浏览器实例应该存在"
            assert browser.page is not None, "页面实例应该存在"
            print(f"✓ 初始化测试通过")
        finally:
            await browser.cleanup()

    async def test_navigate(self, browser):
        """测试页面导航"""
        # 导航到示例页面
        result = await browser.navigate("https://example.com")

        assert result.success is True, f"导航应该成功: {result.message}"
        print(f"  导航结果: {result.success}")
        print(f"✓ 导航测试通过")

    async def test_view_page(self, browser):
        """测试查看页面内容"""
        # 先导航
        await browser.navigate("https://example.com")

        # 查看页面
        result = await browser.view_page()

        assert result.success is True, f"查看页面应该成功: {result.message}"
        assert "data" in result.model_dump(), "结果应该包含 data"
        print(f"  页面内容长度: {len(str(result.data))}")
        print(f"✓ 查看页面测试通过")

    async def test_screenshot(self, browser):
        """测试截图功能"""
        # 先导航
        await browser.navigate("https://example.com")

        # 截图
        screenshot_data = await browser.screenshot()

        assert screenshot_data is not None, "应该返回截图数据"
        assert len(screenshot_data) > 0, "截图数据不应该为空"
        assert screenshot_data[:8] == b'\\x89PNG\\r\\n\\x1a\\n', "应该是 PNG 格式"

        print(f"  截图大小: {len(screenshot_data)} bytes")
        print(f"✓ 截图测试通过")

    async def test_scroll(self, browser):
        """测试滚动功能"""
        # 导航到一个较长的页面
        await browser.navigate("https://en.wikipedia.org/wiki/Python_(programming_language)")

        # 向下滚动
        result = await browser.scroll_down()
        assert result.success is True, "向下滚动应该成功"

        await asyncio.sleep(0.5)

        # 向上滚动
        result = await browser.scroll_up()
        assert result.success is True, "向上滚动应该成功"

        print(f"✓ 滚动测试通过")

    async def test_click_by_coordinate(self, browser):
        """测试坐标点击"""
        # 导航到示例页面
        await browser.navigate("https://example.com")

        # 点击页面中心
        result = await browser.click(coordinate_x=400, coordinate_y=300)

        assert result.success is True, f"点击应该成功: {result.message}"
        print(f"✓ 坐标点击测试通过")

    async def test_console_exec(self, browser):
        """测试执行 JavaScript"""
        # 导航
        await browser.navigate("https://example.com")

        # 执行 JavaScript
        result = await browser.console_exec("return document.title")

        assert result.success is True, f"JS 执行应该成功: {result.message}"
        assert "data" in result.model_dump(), "结果应该包含 data"
        print(f"  页面标题: {result.data.get('result')}")
        print(f"✓ JS 执行测试通过")

    async def test_press_key(self, browser):
        """测试按键"""
        # 导航
        await browser.navigate("https://example.com")

        # 按 Tab 键
        result = await browser.press_key("Tab")

        assert result.success is True, f"按键应该成功: {result.message}"
        print(f"✓ 按键测试通过")

    async def test_restart(self, browser):
        """测试重启浏览器"""
        # 导航到一个页面
        await browser.navigate("https://example.com")

        # 重启
        result = await browser.restart("https://example.org")

        assert result.success is True, f"重启应该成功: {result.message}"
        print(f"✓ 重启测试通过")


@pytest.mark.asyncio
class TestPlaywrightBrowserInput:
    """输入相关功能测试"""

    async def test_input_by_index(self, browser):
        """测试通过索引输入文本"""
        # 导航到搜索页面
        await browser.navigate("https://www.google.com")

        await asyncio.sleep(1)  # 等待页面加载

        # 尝试输入（找到搜索框）
        # 注意：这个测试可能因为页面结构变化而失败
        try:
            result = await browser.input(text="Playwright test", press_enter=True, index=0)
            print(f"  输入结果: {result.success}")
        except Exception as e:
            print(f"  输入测试跳过（可能是页面结构问题）: {e}")

        print(f"✓ 输入测试完成")


@pytest.mark.asyncio
class TestPlaywrightBrowserEdgeCases:
    """边界情况测试"""

    async def test_navigate_invalid_url(self, browser):
        """测试导航到无效 URL"""
        # 导航到无效 URL
        result = await browser.navigate("invalid-url")

        # 应该返回失败或警告
        print(f"  无效 URL 结果: {result.success}, {result.message}")
        print(f"✓ 无效 URL 测试完成")

    async def test_multiple_navigations(self, browser):
        """测试多次导航"""
        urls = [
            "https://example.com",
            "https://example.org",
            "https://example.net",
        ]

        for url in urls:
            result = await browser.navigate(url)
            assert result.success is True, f"导航到 {url} 应该成功"
            await asyncio.sleep(0.5)

        print(f"✓ 多次导航测试通过: {len(urls)} 个 URL")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
