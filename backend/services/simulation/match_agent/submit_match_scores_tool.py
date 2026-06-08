"""submit_match_scores 工具。"""

from code.library.agent_atoms.tools.tool_def import Tool


def make_submit_tool() -> Tool:
    """创建 submit_match_scores 工具。"""
    def submit_fn(scores: list) -> dict:
        return {"success": True}

    return Tool(
        name="submit_match_scores",
        description="提交一批模式的情境匹配度评分。",
        parameters={
            "type": "object",
            "properties": {
                "scores": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "score": {"type": "number"},
                            "reason": {"type": "string"},
                        },
                        "required": ["name", "score"],
                    },
                }
            },
            "required": ["scores"],
        },
        fn=submit_fn,
    )
