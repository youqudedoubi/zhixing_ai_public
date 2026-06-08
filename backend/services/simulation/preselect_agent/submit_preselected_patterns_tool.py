"""submit_preselected_patterns 工具。"""

from code.library.agent_atoms.tools.tool_def import Tool


def make_submit_tool() -> Tool:
    """创建 submit_preselected_patterns 工具。"""
    def submit_fn(patterns: list) -> dict:
        return {"success": True}

    return Tool(
        name="submit_preselected_patterns",
        description="提交预选的模式列表。",
        parameters={
            "type": "object",
            "properties": {
                "patterns": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["name", "reason"],
                    },
                    "description": "预选的模式列表，每项包含name和reason",
                }
            },
            "required": ["patterns"],
        },
        fn=submit_fn,
    )
