"""submit_simulation_result 工具。"""

from code.library.agent_atoms.tools.tool_def import Tool


def make_submit_tool() -> Tool:
    """创建 submit_simulation_result 工具。"""
    def submit_fn(content: str) -> dict:
        return {"success": True}

    return Tool(
        name="submit_simulation_result",
        description="提交当前节点的模拟结果文本。",
        parameters={
            "type": "object",
            "properties": {"content": {"type": "string", "description": "模拟结果文本"}},
            "required": ["content"],
        },
        fn=submit_fn,
    )
