"""Baidu 搜索实现"""

import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from manus_web_agent.domain.external.search import SearchEngine
from manus_web_agent.domain.models.search import SearchResult, SearchResults

logger = logging.getLogger(__name__)


class BaiduSearchEngine(SearchEngine):
    """Baidu 搜索实现（网页抓取）"""

    def __init__(self):
        self.base_url = "https://www.baidu.com/s"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    async def search(
        self, query: str, num_results: int = 10, recency_days: Optional[int] = None
    ) -> SearchResults:
        """搜索

        :param query: 搜索查询
        :param num_results: 结果数量
        :param recency_days: 最近天数限制（百度不支持精确天数，只支持24小时内）
        :return: 搜索结果
        """
        params = {"wd": query, "rn": min(num_results, 50)}

        # 添加时间限制（百度只支持24小时内）
        if recency_days and recency_days <= 1:
            params["gpc"] = "stf=1"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url, params=params, headers=self.headers
                )
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            # 解析搜索结果 - 尝试多种选择器
            containers = soup.select(".result") or soup.select(".c-container")

            for item in containers:
                # 尝试多种标题选择器
                title_elem = item.select_one("h3 a") or item.select_one(".t a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                url = title_elem.get("href", "")

                # 尝试多种摘要选择器
                snippet_elem = (
                    item.select_one(".content-right_8Zs40")
                    or item.select_one(".c-abstract")
                    or item.select_one("span[class*='abstract']")
                    or item.select_one("div[class*='abstract']")
                )
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                if url:  # 只添加有链接的结果
                    results.append(
                        SearchResult(title=title, link=url, snippet=snippet)
                    )

                if len(results) >= num_results:
                    break

            return SearchResults(results=results, query=query, data_range=None)

        except Exception as e:
            logger.error(f"Baidu 搜索错误: {e}")
            return SearchResults(results=[], query=query, data_range=None, error=str(e))
