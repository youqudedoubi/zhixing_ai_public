import json

from code.library.agent_atoms.tools.tool_def import Tool


class ToolHub:
    """程序化 tool 索引中心；execute 走 hub，与 SkillHub 对称。"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self.sse_buffer: list[str] = []

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def get_tool_schemas(self) -> list[dict]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def get_schema_function(self, name: str) -> dict | None:
        tool = self.get(name)
        if tool is None:
            return None
        return tool.to_openai_schema().get("function")

    def execute(self, tool_name: str, arguments: str | dict) -> dict:
        if tool_name not in self._tools:
            return {"success": False, "result": f"未知工具：{tool_name}"}

        if isinstance(arguments, str):
            arguments = json.loads(arguments)

        result = self._tools[tool_name].fn(**arguments)
        return {"success": True, "result": result}

    def flush_sse_buffer(self) -> list[str]:
        msgs = self.sse_buffer[:]
        self.sse_buffer.clear()
        return msgs


class ToolRegistry:
    """给具体 agent 使用的 tool 白名单（仅用于组提示词）。"""

    def __init__(self, hub: ToolHub, names: list[str] | None = None):
        self.hub = hub
        self._names: list[str] = []
        self._name_set: set[str] = set()
        if names:
            self.register(names)

    def register(self, names: list[str]) -> None:
        for name in names:
            if name in self._name_set:
                continue
            if not self.hub.get(name):
                continue
            self._names.append(name)
            self._name_set.add(name)

    def list_names(self) -> list[str]:
        return self._names[:]

    def get_tool_schemas(self) -> list[dict]:
        schemas = []
        for name in self._names:
            tool = self.hub.get(name)
            if tool:
                schemas.append(tool.to_openai_schema())
        return schemas
