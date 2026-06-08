"""send_message：向另一个 chat-agent 发送消息。纯消息传递，路由由 loop 负责。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Callable

from code.library.agent_atoms.tools.tool_def import Tool

EmitFn = Callable[[str, str, str], None]  # (agent_name, content, msg_type)


def make_send_message_tool(
    agent_name: str,
    valid_targets: list[str],
    emit: EmitFn,
    process_log: list[dict],
) -> Tool:
    targets_str = ", ".join(valid_targets)

    def fn(to: str, message: str) -> dict:
        if to not in valid_targets:
            return {"error": f"Unknown target '{to}'. Valid targets: {targets_str}"}
        emit(
            agent_name,
            json.dumps({"from": agent_name, "to": to, "message": message}, ensure_ascii=False),
            "handoff",
        )
        process_log.append({
            "agent_name": agent_name,
            "type": "handoff",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "content": {"from": agent_name, "to": to, "message": message},
        })
        return {"delivered": True, "to": to, "message": message}

    return Tool(
        name="send_message",
        description=f"Send a message to another chat-agent. Valid targets: {targets_str}.",
        parameters={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": f"Recipient chat-agent name. One of: {targets_str}"},
                "message": {"type": "string", "description": "The message content."},
            },
            "required": ["to", "message"],
        },
        fn=fn,
    )
