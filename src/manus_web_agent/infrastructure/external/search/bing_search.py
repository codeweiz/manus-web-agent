"""Bing 搜索实现"""

import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from manus_web_agent.domain.external.search import SearchEngine
from manus_web_agent.domain.models.search import SearchResult, SearchResults

logger = logging.getLogger(__name__)


class BingSearchEngine(SearchEngine):
    """Bing 搜索实现（网页抓取）"""

    def __init__(self):
        self.base_url = "https://www.bing.com/search"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def search(
        self, query: str, num_results: int = 10, recency_days: Optional[int] = None
    ) -> SearchResults:
        """搜索

        :param query: 搜索查询
        :param num_results: 结果数量
        :param recency_days: 最近天数限制
        :return: 搜索结果
        """
        params = {"q": query, "count": min(num_results, 50)}

        # 添加时间限制
        if recency_days:
            if recency_days <= 1:
                params["filters"] = "ex1%3a\"ez1\""
            elif recency_days <= 7:
                params["filters"] = "ex1%3a\"ez2\""
            elif recency_days <= 30:
                params["filters"] = "ex1%3a\"ez3\""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url, params=params, headers=self.headers
                )
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            # 解析搜索结果
            for item in soup.select(".b_algo"):
                title_elem = item.select_one("h2 a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                url = title_elem.get("href", "")
                snippet_elem = item.select_one(".b_caption p")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                if url:  # 只添加有链接的结果
                    results.append(
                        SearchResult(title=title, link=url, snippet=snippet)
                    )

                if len(results) >= num_results:
                    break

            return SearchResults(results=results, query=query, data_range=None)

        except Exception as e:
            logger.error(f"Bing 搜索错误: {e}")
            return SearchResults(results=[], query=query, data_range=None, error=str(e))
