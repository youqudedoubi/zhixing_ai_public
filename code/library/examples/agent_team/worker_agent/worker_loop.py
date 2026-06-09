"""worker_loop：send_message 发给上级 → 退出循环，返回消息。"""
import json
from datetime import datetime
from typing import Callable

from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry

EmitFn = Callable[[str, str, str], None]  # (agent_name, content, msg_type)


class WorkerLoop:
    """接收任务 → 执行 → send_message 向上汇报 → 退出。"""

    def __init__(
        self,
        model: BaseModel,
        context: list[dict],
        registry: ToolRegistry,
        agent_name: str,
        emit: EmitFn,
        process_log: list[dict],
        superior_name: str,
    ):
        self.model = model
        self.context = context
        self.registry = registry
        self.agent_name = agent_name
        self.emit = emit
        self.process_log = process_log
        self.superior_name = superior_name

    def _stream_turn(self, messages: list[dict], tools: list[dict]) -> tuple[str, list[dict], str | None]:
        stream = self.model.generate_stream(messages, tools=tools if tools else None)
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_calls_acc: dict[int, dict] = {}
        reasoning_started = False
        content_started = False

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            rc = getattr(delta, "reasoning_content", None)
            if rc:
                reasoning_started = True
                reasoning_parts.append(rc)
                self.emit(self.agent_name, rc, "thinking_token")
            if delta.content:
                content_started = True
                content_parts.append(delta.content)
                self.emit(self.agent_name, delta.content, "text_token")
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls_acc[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_acc[idx]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_calls_acc[idx]["arguments"] += tc.function.arguments

        content = "".join(content_parts)
        reasoning_content = "".join(reasoning_parts) or None
        if reasoning_started:
            self.emit(self.agent_name, "", "thinking_end")
        if content_started:
            self.emit(self.agent_name, "", "text_end")

        tool_calls = [
            {
                "id": tool_calls_acc[i]["id"],
                "type": "function",
                "function": {"name": tool_calls_acc[i]["name"], "arguments": tool_calls_acc[i]["arguments"]},
            }
            for i in sorted(tool_calls_acc)
        ]
        return content, tool_calls, reasoning_content

    def _execute_tools(self, tool_calls: list[dict]) -> list[dict]:
        results = []
        for tc in tool_calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except Exception:
                args = {}
            result = self.registry.execute(name, args)
            results.append({
                "tool_call_id": tc["id"],
                "name": name,
                "args": args,
                "result": json.dumps(result, ensure_ascii=False),
            })
        return results

    def run(self, max_turns: int = 50) -> str:
        tools = self.registry.get_tool_schemas()
        last_content = ""

        for _ in range(max_turns):
            content, tool_calls, reasoning = self._stream_turn(self.context, tools)
            last_content = content or last_content

            if content:
                _log(self.process_log, self.agent_name, "assistant", content, reasoning=reasoning or None)

            assistant_msg: dict = {
                "role": "assistant",
                "content": content or None,
                "tool_calls": tool_calls or None,
            }
            if reasoning:
                assistant_msg["reasoning_content"] = reasoning
            self.context.append(assistant_msg)

            if not tool_calls:
                break

            tool_results = self._execute_tools(tool_calls)
            for tr in tool_results:
                self.emit(
                    self.agent_name,
                    json.dumps({"name": tr["name"], "args": tr.get("args", {}), "result": tr["result"]}, ensure_ascii=False),
                    "tool_call",
                )
                _log(self.process_log, self.agent_name, "tool_call", {
                    "name": tr["name"], "args": tr.get("args", {}), "result": tr["result"],
                })
                self.context.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_call_id"],
                    "content": tr["result"],
                })

                # ── 分派：send_message 发给上级 → 退出循环 ──
                if tr["name"] == "send_message":
                    args = tr.get("args", {})
                    if args.get("to") == self.superior_name:
                        return args.get("message", last_content)

        return last_content


def _log(process_log, agent_name, msg_type, content, reasoning=None):
    process_log.append({
        "agent_name": agent_name,
        "type": msg_type,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "content": content,
        **({"reasoning": reasoning} if reasoning else {}),
    })
