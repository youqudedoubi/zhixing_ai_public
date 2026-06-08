"""submit_thought_flow 工具：将 LLM 生成的思维流内容提交回 agent。"""

from code.library.agent_atoms.tools.tool_def import Tool


def make_submit_tool(result_holder: dict) -> Tool:
    """创建 submit_thought_flow 工具。

    result_holder 用于接收 LLM 提交的思维流内容，
    因为 tool_call_loop 需要从工具执行副作用中获取结果。
    """
    def submit_fn(content: str) -> dict:
        result_holder["content"] = content
        return {"success": True}

    return Tool(
        name="submit_thought_flow",
        description="提交生成的思维流内容（markdown正文，不含frontmatter）。",
        parameters={
            "type": "object",
            "properties": {"content": {"type": "string", "description": "思维流正文内容"}},
            "required": ["content"],
        },
        fn=submit_fn,
    )
