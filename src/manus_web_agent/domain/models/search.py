from typing import Optional, List

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """搜索结果项"""

    title: str = Field(..., description="标题")

    link: str = Field(..., description="链接")

    snippet: str = Field(..., description="摘要")


class SearchResults(BaseModel):
    """搜索结果"""

    query: str = Field(..., description="查询词")

    data_range: Optional[str] = Field(..., description="数据范围")

    total_results: int = Field(default=0, description="总结果数")

    results: List[SearchResultItem] = Field(default_factory=list, description="结果列表")
