import json
from typing import Any
from code.library.agent_atoms.tools.tool_def import Tool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}
        # SSE messages buffered during synchronous tool execution (e.g. research)
        self.sse_buffer: list[str] = []

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_tool_schemas(self) -> list[dict]:
        """返回传给 LLM 的 tools 列表。"""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def execute(self, tool_name: str, arguments: str | dict) -> dict:
        """执行工具，返回统一格式结果。

        Args:
            tool_name: LLM 返回的工具名
            arguments: LLM 返回的 arguments，字符串或已解析的 dict
        """
        if tool_name not in self._tools:
            return {"success": False, "result": f"未知工具：{tool_name}"}

        if isinstance(arguments, str):
            arguments = json.loads(arguments)

        result = self._tools[tool_name].fn(**arguments)
        return {"success": True, "result": result}

    def flush_sse_buffer(self) -> list[str]:
        """Return and clear buffered SSE strings."""
        msgs = self.sse_buffer[:]
        self.sse_buffer.clear()
        return msgs

