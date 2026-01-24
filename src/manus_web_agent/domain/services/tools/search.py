from typing import Optional

from manus_web_agent.domain.external.search import SearchEngine
from manus_web_agent.domain.services.tools.base import BaseTool, tool


class SearchTool(BaseTool):
    """搜索工具"""

    name: str = "search"

    def __init__(self, search_engine: SearchEngine):
        super().__init__()
        self.search_engine = search_engine

    @tool(
        name="info_search_web",
        description="Search the web for information. Use for finding information on a specific topic.",
        parameters={
            "query": {
                "type": "string",
                "description": "Query to search for."
            },
            "date_range": {
                "type": "string",
                "enum": ["all", "past_hour", "past_day", "past_week", "past_month", "past_year"],
                "description": "Optional. Date range to search within."
            }
        },
        required=["query"],
    )
    async def info_search_web(self, query: str, date_range: Optional[str] = None):
        """搜索网页"""
        return await self.search_engine.search(query, date_range)
