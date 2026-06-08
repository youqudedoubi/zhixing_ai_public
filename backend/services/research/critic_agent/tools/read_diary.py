"""read_diary：按日期读取日记原文。"""
from __future__ import annotations

from pathlib import Path

from code.library.agent_atoms.tools.tool_def import Tool
from code.shared.data_paths import DIARY_DIR
from code.shared.validate_path import validate_path


def make_read_diary_tool(allowed_root: Path) -> Tool:
    diary_dir = allowed_root / DIARY_DIR

    def fn(date: str) -> str:
        for ext in (".md", ".txt"):
            try:
                diary_path = validate_path(f"{date}{ext}", diary_dir)
            except ValueError:
                continue
            if diary_path.exists():
                return diary_path.read_text(encoding="utf-8", errors="replace")
        return f"Diary entry for '{date}' not found."

    return Tool(
        name="read_diary",
        description="Read a diary entry by date string, e.g. '2024-01-01'.",
        parameters={
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date string like '2024-01-01'"},
            },
            "required": ["date"],
        },
        fn=fn,
    )
