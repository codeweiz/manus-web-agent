from typing import Protocol, List, Dict, Optional, Any


class LLM(Protocol):
    """大语言模型服务网关接口"""

    async def ask(
            self,
            messages: List[Dict[str, str]],
            tools: Optional[List[Dict[str, Any]]] = None,
            response_format: Optional[Dict[str, Any]] = None,
            tool_choice: Optional[str] = None
    ) -> Dict[str, Any]:
        """发送问答请求给 LLM
        :param messages: 消息列表
        :param tools: 工具列表
        :param response_format: 响应格式
        :param tool_choice: 工具选择
        :return: 响应
        """
        pass

    @property
    def model_name(self) -> str:
        """获取模型名"""
        pass

    @property
    def temperature(self) -> float:
        """获取温度"""
        pass

    @property
    def max_tokens(self) -> int:
        """获取最大 token 数"""
        pass
