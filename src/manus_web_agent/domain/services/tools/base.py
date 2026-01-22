import inspect
from typing import Dict, Any, List, Callable

from manus_web_agent.domain.models.tool_result import ToolResult


def tool(
        name: str,
        description: str,
        parameters: Dict[str, Dict[str, Any]],
        required: List[str]
) -> Callable:
    """工具装饰器
    :param name: 工具名
    :param description: 工具描述
    :param parameters: 工具参数
    :param required: 工具必填参数
    :return: 工具函数
    """

    def decorator(func: Callable) -> Callable:
        """工具装饰器"""
        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required,
                },
            }
        }

        func._function_name = name
        func._tool_description = description
        func._tool_schema = schema

        return func

    return decorator


class BaseTool:
    """基础工具"""

    name: str = ""

    def __init__(self):

        self._tools_cache = None

    def get_tools(self) -> List[Dict[str, Any]]:
        """获取已注册的工具列表
        :return: 工具列表
        """

        if self._tools_cache is not None:
            return self._tools_cache

        tools = []
        for _, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, "_tool_schema"):
                tools.append(method._tool_schema)

        self._tools_cache = tools
        return tools

    def has_function(self, function_name: str) -> bool:
        """检查是否具有指定工具
        :param function_name: 工具名
        :return: 是否具有工具
        """
        for _, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, "_function_name") and method._function_name == function_name:
                return True
        return False

    def _filter_parameters(self, method: Callable, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """过滤工具参数
        :param method: 工具方法
        :param kwargs: 参数字典
        :return: 过滤后的参数字典
        """

        sig = inspect.signature(method)

        filters_kwargs = {}
        for param_name, param_value in kwargs.items():
            if param_name in sig.parameters:
                filters_kwargs[param_name] = kwargs[param_value]

        return filters_kwargs

    async def invoke_function(self, function_name: str, **kwargs) -> ToolResult:
        """调用工具
        :param function_name: 工具名
        :param kwargs: 参数字典
        :return: 工具执行结果
        """

        for _, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, "_function_name") and method._function_name == function_name:
                filtered_kwargs = self._filter_parameters(method, kwargs)
                return await method(**filtered_kwargs)

        raise ValueError(f"Tool '{function_name}' not found")
