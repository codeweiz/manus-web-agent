"""搜索引擎模块"""

from manus_web_agent.core.toml_config import TOML_CONFIG
from manus_web_agent.domain.external.search import SearchEngine
from manus_web_agent.infrastructure.external.search.baidu_search import BaiduSearchEngine
from manus_web_agent.infrastructure.external.search.bing_search import BingSearchEngine
from manus_web_agent.infrastructure.external.search.google_search import GoogleSearchEngine


def get_search_engine() -> SearchEngine:
    """获取配置的搜索引擎

    :return: 搜索引擎实例
    """
    provider = TOML_CONFIG.search_config.provider.lower()

    if provider == "google":
        return GoogleSearchEngine()
    elif provider == "baidu":
        return BaiduSearchEngine()
    elif provider == "bing":
        return BingSearchEngine()
    else:
        # 默认使用 Bing
        return BingSearchEngine()


__all__ = [
    "SearchEngine",
    "GoogleSearchEngine",
    "BingSearchEngine",
    "BaiduSearchEngine",
    "get_search_engine",
]
