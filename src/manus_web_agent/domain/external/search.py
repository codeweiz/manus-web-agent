from typing import Protocol, Optional

from manus_web_agent.domain.models.search import SearchResults
from manus_web_agent.domain.models.tool_result import ToolResult


class SearchEngine(Protocol):
    """搜索引擎服务网关接口"""

    async def search(self, query: str, date_range: Optional[str] = None) -> ToolResult[SearchResults]:
        """搜索
        :param query: 查询词
        :param date_range: 日期范围
        :return: 搜索结果
        """
        pass
