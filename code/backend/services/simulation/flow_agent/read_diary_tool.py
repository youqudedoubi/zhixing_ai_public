"""read_diary 工具：让 LLM 按日期查阅日记片段以补充上下文。"""

from pathlib import Path

from code.library.agent_atoms.tools.tool_def import Tool


def make_read_diary_tool(root: Path) -> Tool:
    """创建 read_diary 工具。"""
    def fn(date: str) -> dict:
        diary_path = root / "raw" / "diary" / f"{date}.md"
        if not diary_path.exists():
            return {"error": f"日记不存在: {date}"}
        return {"content": diary_path.read_text(encoding="utf-8")}

    return Tool(
        name="read_diary",
        description="读取指定日期的日记内容。",
        parameters={
            "type": "object",
            "properties": {"date": {"type": "string", "description": "日期，格式 YYYY-MM-DD"}},
            "required": ["date"],
        },
        fn=fn,
    )
