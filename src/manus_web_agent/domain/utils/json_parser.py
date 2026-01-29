from typing import Protocol, Optional, Any, Union, Dict, List


class JsonParser(Protocol):
    """JSON 解析器接口"""

    async def parse(self, text: str, default_value: Optional[Any] = None) -> Union[Dict, List, Any]:
        """解析 LLM 输出的字符串为 JSON
        如果本地解析策略失败，则回退到使用 LLM 解析

        :param text: LLM 的原始字符串输出
        :param default_value: 解析失败时返回的默认值
        :return: 解析后的 JSON 对象（字典、列表或其他 JSON 可序列化类型）

        :raises ValueError: 如果所有解析策略都失败且没有提供默认值
        """
