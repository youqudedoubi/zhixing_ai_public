"""research 工具：将 Agent Team 包装为可供主 chat-agent 调用的 Tool。

子 agent 的 SSE 事件在同步执行期间写入 tool_hub.sse_buffer，
chat_agent 的 ToolCallLoop 在工具返回后 flush。
"""
from __future__ import annotations

import json
from pathlib import Path

from code.library.agent_atoms.tools.tool_def import Tool
from code.library.agent_atoms.tools.tools_loader import ToolHub
from code.backend.services.research.agent_team import run_research
from code.backend.services.research.analyze_agent.tools.list_pattern import make_list_pattern_tool


def _list_pattern_text(allowed_root: Path) -> str:
    """列出所有可用模式卡片，供 agent 系统提示使用。"""
    return make_list_pattern_tool(allowed_root).fn()


def make_research_tool(allowed_root: Path, tool_hub: ToolHub) -> Tool:
    """创建 research 工具。

    tool_hub：主 chat-agent 的 hub，子 agent SSE 写入 tool_hub.sse_buffer。
    """

    def fn(topic: str) -> dict:
        if not topic or not topic.strip():
            return {"success": False, "error": "研究课题不能为空"}

        pattern_text = _list_pattern_text(allowed_root)

        def emit(agent_name: str, content: str, msg_type: str) -> None:
            payload = {
                "type": "research_message",
                "agent_name": agent_name,
                "content": content,
                "msg_type": msg_type,
            }
            tool_hub.sse_buffer.append(
                f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            )

        report_path, _log = run_research(
            topic=topic.strip(),
            allowed_root=allowed_root,
            pattern_text=pattern_text,
            emit=emit,
        )

        process_path = str(Path(report_path).parent / "research_process.json")

        return {
            "success": True,
            "report_path": report_path,
            "process_path": process_path,
            "message": f"研究完成。报告已存储到 {report_path}",
        }

    return Tool(
        name="research",
        description=(
            "深度研究用户给定的课题，通过多Agent协作分析日记和模式，生成研究报告。"
            "研究完成后返回报告路径。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "研究课题，例如'我为什么这么在意别人的评价'",
                },
            },
            "required": ["topic"],
        },
        fn=fn,
    )
