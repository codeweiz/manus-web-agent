"""搜索引擎测试 - 使用真实 HTTP 请求

运行测试:
    python -m pytest tests/infrastructure/external/test_search.py -v

注意: 这些测试会发起真实的 HTTP 请求到搜索引擎
"""

import asyncio
import os
import sys

# 确保能导入项目代码
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest

from manus_web_agent.infrastructure.external.search.baidu_search import BaiduSearchEngine
from manus_web_agent.infrastructure.external.search.bing_search import BingSearchEngine
from manus_web_agent.infrastructure.external.search.google_search import GoogleSearchEngine


@pytest.mark.asyncio
class TestBingSearch:
    """Bing 搜索测试"""

    async def test_basic_search(self):
        """测试基本搜索功能"""
        engine = BingSearchEngine()
        results = await engine.search("Python programming", num_results=5)

        assert results is not None, "应该返回搜索结果"
        assert results.query == "Python programming", "查询词应该匹配"
        assert len(results.results) > 0, "应该返回至少一个结果"

        # 检查结果结构
        for result in results.results:
            assert result.title, "结果应该有标题"
            assert result.link, "结果应该有链接"
            print(f"  - {result.title[:50]}... ({result.link[:60]}...)")

        print(f"✓ Bing 基本搜索通过: 找到 {len(results.results)} 个结果")

    async def test_chinese_search(self):
        """测试中文搜索"""
        engine = BingSearchEngine()
        results = await engine.search("人工智能", num_results=5)

        assert results is not None
        assert len(results.results) > 0

        print(f"✓ Bing 中文搜索通过: 找到 {len(results.results)} 个结果")

    async def test_empty_results(self):
        """测试无结果搜索"""
        engine = BingSearchEngine()
        # 使用一个非常特殊的查询，可能返回空结果
        results = await engine.search("xyzabc12345nonexistent", num_results=5)

        # Bing 通常会返回一些结果，即使是奇怪的查询
        assert results is not None

        print(f"✓ Bing 空结果测试通过: {len(results.results)} 个结果")

    async def test_result_structure(self):
        """测试搜索结果结构"""
        engine = BingSearchEngine()
        results = await engine.search("OpenAI", num_results=3)

        for result in results.results:
            assert hasattr(result, 'title')
            assert hasattr(result, 'link')
            assert hasattr(result, 'snippet')
            assert isinstance(result.title, str)
            assert isinstance(result.link, str)
            assert isinstance(result.snippet, str)

        print(f"✓ Bing 结果结构测试通过")


@pytest.mark.asyncio
class TestBaiduSearch:
    """Baidu 搜索测试"""

    async def test_basic_search(self):
        """测试基本搜索功能"""
        engine = BaiduSearchEngine()
        results = await engine.search("Python", num_results=5)

        assert results is not None, "应该返回搜索结果"
        assert results.query == "Python", "查询词应该匹配"
        # Baidu 可能有反爬机制，结果可能为空

        if len(results.results) > 0:
            for result in results.results:
                assert result.title, "结果应该有标题"
                print(f"  - {result.title[:50]}...")

        print(f"✓ Baidu 基本搜索通过: 找到 {len(results.results)} 个结果")

    async def test_chinese_search(self):
        """测试中文搜索"""
        engine = BaiduSearchEngine()
        results = await engine.search("百度", num_results=5)

        assert results is not None

        print(f"✓ Baidu 中文搜索通过: 找到 {len(results.results)} 个结果")


@pytest.mark.asyncio
class TestGoogleSearch:
    """Google 搜索测试 (需要 API Key)"""

    async def test_search_without_config(self):
        """测试无配置时的行为"""
        engine = GoogleSearchEngine()

        # 如果没有配置 API key，应该抛出异常或返回空结果
        try:
            results = await engine.search("Python", num_results=5)
            # 如果有配置，检查结果
            assert results is not None
            print(f"✓ Google 搜索通过: 找到 {len(results.results)} 个结果 (已配置)")
        except ValueError as e:
            assert "api_key" in str(e).lower() or "engine_id" in str(e).lower()
            print(f"✓ Google 搜索跳过: 未配置 API Key ({e})")


@pytest.mark.asyncio
class TestSearchComparison:
    """搜索引擎对比测试"""

    async def test_same_query_different_engines(self):
        """测试相同查询在不同引擎的结果"""
        query = "Python programming language"

        # Bing
        bing = BingSearchEngine()
        bing_results = await bing.search(query, num_results=3)

        # Baidu
        baidu = BaiduSearchEngine()
        baidu_results = await baidu.search(query, num_results=3)

        print(f"\n查询: '{query}'")
        print(f"  Bing:   {len(bing_results.results)} 个结果")
        print(f"  Baidu:  {len(baidu_results.results)} 个结果")

        # 至少有一个引擎应该返回结果
        total_results = len(bing_results.results) + len(baidu_results.results)
        assert total_results > 0, "至少一个引擎应该返回结果"

        print(f"✓ 跨引擎对比测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
