import json

from code.library.agent_atoms.context_def import BaseContextManager
from code.library.agent_atoms.llm import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry


class ToolCallLoop:
    def __init__(
        self,
        model: BaseModel,
        context_manager: BaseContextManager,
        tool_registry: ToolRegistry,
    ):
        self.model = model
        self.tool_registry = tool_registry
        self.context_manager = context_manager

    def run(self, message: str, max_turns: int = 10) -> str:
        self.context_manager.add({"role": "user", "content": message})
        for _ in range(max_turns):
            messages = self.context_manager.get_messages()
            response = self.model.generate_nonstream(
                messages,
                tools=self.tool_registry.get_tool_schemas(),
            )
            msg = response.choices[0].message

            if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                print("\n[思考过程]")
                print(msg.reasoning_content)
            if msg.content:
                print("\n[AI回复]")
                print(msg.content)
            if not msg.tool_calls:
                return msg.content or ""
            self.context_manager.add({"role": "assistant", "content": msg.content})
            self.context_manager.add(msg)
            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                args = tool_call.function.arguments
                print("\n[工具调用]", name, "| 参数:", args)
                result = self.tool_registry.execute(name, args)
                print("[工具结果]", result)
                self.context_manager.add(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
        return "超出最大轮次"
