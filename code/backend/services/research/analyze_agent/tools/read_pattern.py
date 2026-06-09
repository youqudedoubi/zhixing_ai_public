"""read_pattern：读取模式卡片全文。"""
from __future__ import annotations

from pathlib import Path

from code.library.agent_atoms.tools.tool_def import Tool
from code.shared.data_paths import PATTERN_DIR
from code.shared.validate_path import validate_path


def make_read_pattern_tool(allowed_root: Path) -> Tool:
    pattern_root = allowed_root / PATTERN_DIR

    def fn(pattern_name: str) -> str:
        for category in ("positive", "negative", "neutral"):
            try:
                card_path = validate_path(f"{category}/{pattern_name}/pattern.md", pattern_root)
            except ValueError:
                continue
            if card_path.exists():
                return card_path.read_text(encoding="utf-8", errors="replace")
        return f"Pattern '{pattern_name}' not found."

    return Tool(
        name="read_pattern",
        description="Read the full content of a pattern card by its folder name.",
        parameters={
            "type": "object",
            "properties": {
                "pattern_name": {"type": "string", "description": "The folder name of the pattern, e.g. '灾难化思维'"},
            },
            "required": ["pattern_name"],
        },
        fn=fn,
    )
