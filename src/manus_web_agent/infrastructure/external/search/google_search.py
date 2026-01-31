"""Google 搜索实现"""

import logging
from typing import Optional

import httpx

from manus_web_agent.core.toml_config import TOML_CONFIG
from manus_web_agent.domain.external.search import SearchEngine
from manus_web_agent.domain.models.search import SearchResult, SearchResults

logger = logging.getLogger(__name__)


class GoogleSearchEngine(SearchEngine):
    """Google 搜索实现（使用 Google Custom Search API）"""

    def __init__(self):
        config = TOML_CONFIG.search_config
        self.api_key = config.api_key
        self.engine_id = config.engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    async def search(
        self, query: str, num_results: int = 10, recency_days: Optional[int] = None
    ) -> SearchResults:
        """搜索

        :param query: 搜索查询
        :param num_results: 结果数量
        :param recency_days: 最近天数限制
        :return: 搜索结果
        """
        if not self.api_key or not self.engine_id:
            raise ValueError("Google 搜索需要配置 api_key 和 engine_id")

        params = {
            "key": self.api_key,
            "cx": self.engine_id,
            "q": query,
            "num": min(num_results, 10),
        }

        # 添加时间限制
        if recency_days:
            if recency_days <= 1:
                params["dateRestrict"] = "d1"
            elif recency_days <= 7:
                params["dateRestrict"] = "w1"
            elif recency_days <= 30:
                params["dateRestrict"] = "m1"
            elif recency_days <= 365:
                params["dateRestrict"] = "y1"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("items", []):
                link = item.get("link", "")
                if link:  # 只添加有链接的结果
                    results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            link=link,
                            snippet=item.get("snippet", ""),
                        )
                    )

            return SearchResults(results=results, query=query, data_range=None)

        except Exception as e:
            logger.error(f"Google 搜索错误: {e}")
            return SearchResults(results=[], query=query, data_range=None, error=str(e))
