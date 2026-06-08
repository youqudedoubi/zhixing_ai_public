from datetime import datetime

from code.library.agent_atoms.tools.tool_def import Tool


def _get_time() -> str:
    return datetime.now().isoformat(timespec="seconds")


def make_get_time_tool() -> Tool:
    def fn() -> str:
        return _get_time()

    return Tool(
        name="get_time",
        description="Get current local time in ISO format.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=fn,
    )
