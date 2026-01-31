"""LLM JSON 解析器实现

实现多种解析策略，从 LLM 输出中提取有效的 JSON。
"""

import json
import logging
import re
from typing import Any, Optional, Union

from manus_web_agent.domain.external.llm import LLM
from manus_web_agent.domain.utils.json_parser import JsonParser

logger = logging.getLogger(__name__)


class LLMJsonParser(JsonParser):
    """LLM JSON 解析器

    解析策略（按优先级）：
    1. DIRECT - 直接解析
    2. MARKDOWN_BLOCK - 提取 markdown 代码块
    3. CLEANUP_AND_PARSE - 清理格式问题后解析
    4. LLM_EXTRACT_AND_FIX - 使用 LLM 提取和修复
    """

    def __init__(self, llm: Optional[LLM] = None):
        self._llm = llm
        self._max_retries = 3

    async def parse(
        self, text: str, default_value: Optional[Any] = None
    ) -> Union[dict, list, Any]:
        """解析 LLM 输出的字符串为 JSON

        :param text: LLM 的原始字符串输出
        :param default_value: 解析失败时返回的默认值
        :return: 解析后的 JSON 对象
        :raises ValueError: 如果所有解析策略都失败且没有提供默认值
        """
        if not text or not text.strip():
            if default_value is not None:
                return default_value
            raise ValueError("输入文本为空")

        # 策略 1: 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 策略 2: 提取 markdown 代码块
        try:
            result = self._extract_from_markdown(text)
            if result:
                return result
        except Exception:
            pass

        # 策略 3: 清理后解析
        try:
            cleaned = self._cleanup_json_text(text)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 策略 4: 使用 LLM 提取和修复
        if self._llm:
            try:
                result = await self._extract_with_llm(text)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"LLM 提取失败: {e}")

        # 所有策略都失败
        if default_value is not None:
            return default_value

        raise ValueError(f"无法解析 JSON: {text[:200]}...")

    def _extract_from_markdown(self, text: str) -> Optional[Any]:
        """从 markdown 代码块中提取 JSON"""
        # 匹配 ```json ... ``` 或 ``` ... ```
        patterns = [
            r"```json\s*\n(.*?)\n```",
            r"```\s*\n(.*?)\n```",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

        return None

    def _cleanup_json_text(self, text: str) -> str:
        """清理 JSON 文本中的常见问题"""
        # 移除开头的 BOM
        text = text.lstrip("\ufeff")

        # 移除开头的非 JSON 字符
        text = re.sub(r"^[^{\[]+", "", text)

        # 移除结尾的非 JSON 字符
        text = re.sub(r"[^}\]]+$", "", text)

        # 修复单引号
        text = text.replace("'", '"')

        # 修复尾部逗号
        text = re.sub(r",(\s*[}\]])", r"\1", text)

        # 修复未加引号的键
        text = re.sub(r"([{,]\s*)(\w+)(\s*:)", r'\1"\2"\3', text)

        # 转义未转义的引号
        text = self._escape_unescaped_quotes(text)

        return text

    def _escape_unescaped_quotes(self, text: str) -> str:
        """转义未转义的引号"""
        result = []
        in_string = False
        escaped = False

        for char in text:
            if char == '"' and not escaped:
                in_string = not in_string
                result.append(char)
            elif char == '"' and in_string and not escaped:
                # 字符串内的未转义引号
                result.append('\\"')
            elif char == "\\" and not escaped:
                escaped = True
                result.append(char)
            else:
                escaped = False
                result.append(char)

        return "".join(result)

    async def _extract_with_llm(self, text: str) -> Optional[Any]:
        """使用 LLM 提取和修复 JSON"""
        if not self._llm:
            return None

        prompt = f"""请从以下文本中提取有效的 JSON。

文本内容：
{text}

要求：
1. 只返回提取的 JSON，不要有任何其他说明
2. 如果文本包含 markdown 代码块，提取其中的 JSON
3. 确保返回的是有效的 JSON 格式
4. 如果无法提取有效的 JSON，返回空对象 {{}}

JSON 输出："""

        for attempt in range(self._max_retries):
            try:
                response = await self._llm.ask(
                    [{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )

                content = response.get("content", "")
                if content:
                    return json.loads(content)

            except Exception as e:
                logger.warning(f"LLM 提取尝试 {attempt + 1} 失败: {e}")
                continue

        return None
