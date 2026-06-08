"""tool_call_loop：simulate_agent 的 LLM 循环。

独立副本（与其他 agent 的 tool_call_loop 同名同理，但各自演化）。
"""

import json

from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry


def run_loop(
    model: BaseModel,
    registry: ToolRegistry,
    system_prompt: str,
    user_message: str,
    target_tool: str,
    max_turns: int = 10,
) -> dict | None:
    """运行 LLM 循环直到 target_tool 被调用。

    返回解析后的工具参数字典；若在 max_turns 内目标工具从未被调用，返回 None。
    """
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    tools = registry.get_tool_schemas()

    for _ in range(max_turns):
        resp = model.generate_nonstream(messages, tools=tools)
        msg = resp.choices[0].message
        content = msg.content or ""
        tool_calls = []
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                })

        assistant_msg: dict = {"role": "assistant", "content": content or None}
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning:
            assistant_msg["reasoning_content"] = reasoning
        messages.append(assistant_msg)

        if not tool_calls:
            break

        for tc in tool_calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except Exception:
                args = {}
            result = registry.execute(name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })
            if name == target_tool:
                return args

    return None
