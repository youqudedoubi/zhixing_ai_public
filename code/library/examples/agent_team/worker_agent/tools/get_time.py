"""get_time：获取当前时间。worker 可用此工具完成任务。"""
from datetime import datetime

from code.library.agent_atoms.tools.tool_def import Tool


def make_get_time_tool() -> Tool:
    def fn() -> str:
        return datetime.now().isoformat(timespec="seconds")

    return Tool(
        name="get_time",
        description="获取当前日期和时间。",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=fn,
    )
