import asyncio
import logging
from typing import List, Dict, Any, Optional

from openai import AsyncOpenAI

from manus_web_agent.core.toml_config import TOML_CONFIG
from manus_web_agent.domain.external.llm import LLM

logger = logging.getLogger(__name__)


class OpenAILLM(LLM):
    """OpenAI LLM 实现"""

    def __init__(self):
        config = TOML_CONFIG.llm_config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        self._model_name = config.model
        self._temperature = config.temperature
        self._max_tokens = config.max_tokens
        logger.info(f"初始化 OpenAI LLM，模型: {self._model_name}")

    @property
    def model_name(self) -> str:
        """获取模型名"""
        return self._model_name

    @property
    def temperature(self) -> float:
        """获取温度"""
        return self._temperature

    @property
    def max_tokens(self) -> int:
        """获取最大 token 数"""
        return self._max_tokens

    async def ask(
            self,
            messages: List[Dict[str, str]],
            tools: Optional[List[Dict[str, Any]]] = None,
            response_format: Optional[Dict[str, Any]] = None,
            tool_choice: Optional[str] = None
    ) -> Dict[str, Any]:
        """发送聊天请求到 OpenAI API，带重试机制"""
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries + 1):
            response = None
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))  # 指数退避
                    logger.info(f"重试 OpenAI API 请求 (尝试 {attempt + 1}/{max_retries + 1})，等待 {delay} 秒")
                    await asyncio.sleep(delay)

                if tools:
                    logger.debug(f"发送带工具的请求到 OpenAI，模型: {self._model_name}，尝试: {attempt + 1}")
                    response = await self.client.chat.completions.create(
                        model=self._model_name,
                        temperature=self._temperature,
                        max_tokens=self._max_tokens,
                        messages=messages,
                        tools=tools,
                        response_format=response_format,
                        tool_choice=tool_choice,
                        parallel_tool_calls=False,
                    )
                else:
                    logger.debug(f"发送不带工具的请求到 OpenAI，模型: {self._model_name}，尝试: {attempt + 1}")
                    response = await self.client.chat.completions.create(
                        model=self._model_name,
                        temperature=self._temperature,
                        max_tokens=self._max_tokens,
                        messages=messages,
                        response_format=response_format,
                    )

                logger.debug(f"OpenAI 响应: {response.model_dump()}")

                if not response or not response.choices:
                    error_msg = f"OpenAI API 返回无效响应 (无 choices)，尝试 {attempt + 1}"
                    logger.error(error_msg)
                    if attempt == max_retries:
                        raise ValueError(f"{max_retries + 1} 次尝试后失败: {error_msg}")
                    continue

                return response.choices[0].message.model_dump()

            except Exception as e:
                error_msg = f"调用 OpenAI API 出错，尝试 {attempt + 1}: {str(e)}"
                logger.error(error_msg)
                if attempt == max_retries:
                    raise e
                continue
