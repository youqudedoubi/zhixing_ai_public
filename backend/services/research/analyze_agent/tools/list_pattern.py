"""list_pattern：列出所有可用模式卡片。"""
from __future__ import annotations

from pathlib import Path

from code.library.agent_atoms.tools.tool_def import Tool
from code.shared.data_paths import PATTERN_DIR


def make_list_pattern_tool(allowed_root: Path) -> Tool:
    pattern_root = allowed_root / PATTERN_DIR

    def fn() -> str:
        lines = []
        for category in ("positive", "negative", "neutral"):
            cat_dir = pattern_root / category
            if not cat_dir.exists():
                continue
            names = [p.name for p in cat_dir.iterdir() if p.is_dir()]
            if names:
                lines.append(f"{category}: {', '.join(sorted(names))}")
        return "\n".join(lines) if lines else "No patterns found."

    return Tool(
        name="list_pattern",
        description="List all available pattern card names grouped by category. Call this first to know which patterns you can read.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=fn,
    )
