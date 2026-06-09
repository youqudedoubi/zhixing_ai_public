"""write_report：将研究报告写入文件。"""
from __future__ import annotations

from pathlib import Path

from code.library.agent_atoms.tools.tool_def import Tool


def make_write_report_tool(report_path: Path) -> Tool:
    def fn(content: str) -> str:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(content, encoding="utf-8")
        return f"Report written to {report_path}"

    return Tool(
        name="write_report",
        description="Write the final research report. Call this once when the research is complete.",
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Full markdown content of the research report."},
            },
            "required": ["content"],
        },
        fn=fn,
    )
