import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncGenerator

from code.backend.models.schemas import Message, ToolCallInfo
from code.backend.services.chat_agent.loop.events import (
    LoopEvent,
    LoopResult,
    RawSSE,
    TextToken,
    ThinkingEnd,
    ThinkingStart,
    ThinkingToken,
    ToolCallResult,
    ToolCallStart,
)
from code.backend.services.chat_agent.tools.pattern_events import extract_pattern_event
from code.library.agent_atoms.context_def import BaseContextManager
from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.tools.tools_loader import ToolHub


@dataclass
class ToolExecutionResult:
    """单次工具调用完成后的结构化结果。

    替代之前的三元素裸 tuple (message_entry, tool_call_info, pattern_event)，
    避免调用方用 isinstance(item, tuple) 做隐式类型判别。
    """

    message_entry: dict
    tool_call_info: ToolCallInfo
    pattern_event: dict | None


async def _iterate_stream(stream) -> AsyncGenerator[object, None]:
    """将同步流式生成器桥接到异步世界。"""
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def drain_stream():
        try:
            for chunk in stream:
                loop.call_soon_threadsafe(queue.put_nowait, chunk)
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, exc)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    loop.run_in_executor(None, drain_stream)

    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        if isinstance(chunk, Exception):
            raise chunk
        yield chunk


class ToolCallLoop:
    """LLM 调用 + 工具执行的核心循环。

    每轮对话：调用模型流式接口 → 累积回复 → 如有 tool_call 则逐个执行 →
    将结果反馈给模型 → 循环（最多 max_turns 轮）。
    """

    def __init__(
        self,
        model: BaseModel,
        tool_hub: ToolHub,
        context_manager: BaseContextManager,
    ):
        self.model = model
        self.tool_hub = tool_hub
        self.context_manager = context_manager

    async def _execute_tool_call(
        self,
        tool_call: dict,
    ) -> AsyncGenerator[LoopEvent | ToolExecutionResult, None]:
        """执行单个工具调用，yield 进度事件，最后 yield ToolExecutionResult。"""
        tool_name = tool_call["function"]["name"]
        args_raw = tool_call["function"]["arguments"]
        try:
            arguments = json.loads(args_raw)
        except Exception:
            arguments = args_raw

        yield ToolCallStart(
            name=tool_name,
            arguments=arguments if isinstance(arguments, dict) else {"_raw": arguments},
        )

        # 在独立线程中执行工具，避免阻塞事件循环
        tool_task = asyncio.create_task(
            asyncio.to_thread(self.tool_hub.execute, tool_name, arguments)
        )
        while not tool_task.done():
            await asyncio.sleep(0.1)
            for buffered in self.tool_hub.flush_sse_buffer():
                yield RawSSE(data=buffered)

        result = await tool_task
        for buffered in self.tool_hub.flush_sse_buffer():
            yield RawSSE(data=buffered)

        result_str = json.dumps(result, ensure_ascii=False)
        yield ToolCallResult(name=tool_name, result=result_str)

        message_entry = {
            "role": "tool",
            "tool_call_id": tool_call.get("id", tool_name),
            "content": result_str,
        }
        tool_call_info = ToolCallInfo(
            tool_name=tool_name,
            arguments=arguments if isinstance(arguments, dict) else {},
            result=result_str,
            call_id=tool_call.get("id"),
        )
        yield ToolExecutionResult(
            message_entry=message_entry,
            tool_call_info=tool_call_info,
            pattern_event=extract_pattern_event(tool_name, result),
        )

    async def _execute_tool_calls(
        self,
        tool_calls: list[dict],
    ) -> AsyncGenerator[LoopEvent | ToolExecutionResult, None]:
        """依次执行本轮所有工具调用，逐个透传事件和结果。"""
        for tool_call in tool_calls:
            async for item in self._execute_tool_call(tool_call):
                yield item

    async def run(
        self,
        tools: list[dict],
        max_turns: int = 15,
    ) -> AsyncGenerator[LoopEvent | LoopResult, None]:
        new_messages: list[Message] = []
        pattern_events: list[dict] = []

        for _ in range(max_turns):
            # ── 第 1 步：调用模型流式接口 ──
            stream = await asyncio.to_thread(
                self.model.generate_stream,
                self.context_manager.get_messages(),
                tools=tools,
            )

            thinking_parts: list[str] = []
            content_parts: list[str] = []
            thinking_started = False

            # tool_call 在流式 API 中可能分多个 chunk 到达：
            # 每个 chunk 带一个 index 标识是第几个 tool_call，
            # arguments 是增量 JSON 片段，需要拼接。
            # 参考 OpenAI/DeepSeek 流式 tool_call 协议。
            accumulated_tool_calls: list[dict] = []

            async for chunk in _iterate_stream(stream):
                delta = chunk.choices[0].delta

                # reasoning / thinking tokens
                if getattr(delta, "reasoning_content", None):
                    if not thinking_started:
                        yield ThinkingStart()
                        thinking_started = True
                    token = delta.reasoning_content
                    thinking_parts.append(token)
                    yield ThinkingToken(token=token)

                # 普通文本 tokens
                if getattr(delta, "content", None):
                    if thinking_started:
                        yield ThinkingEnd()
                        thinking_started = False
                    token = delta.content
                    content_parts.append(token)
                    yield TextToken(token=token)

                # 流式 tool_call 分片：按 index 累积
                if getattr(delta, "tool_calls", None):
                    for tool_call in delta.tool_calls:
                        index = getattr(tool_call, "index", 0)
                        while len(accumulated_tool_calls) <= index:
                            accumulated_tool_calls.append({})
                        entry = accumulated_tool_calls[index]
                        if tool_call.id:
                            entry["id"] = tool_call.id
                        if tool_call.type:
                            entry["type"] = tool_call.type
                        if tool_call.function:
                            if "function" not in entry:
                                entry["function"] = {"name": "", "arguments": ""}
                            if tool_call.function.name:
                                entry["function"]["name"] = tool_call.function.name
                            if tool_call.function.arguments:
                                entry["function"]["arguments"] += tool_call.function.arguments

            if thinking_started:
                yield ThinkingEnd()

            # ── 第 2 步：整理本轮响应 ──
            full_reply = "".join(content_parts)
            full_thinking = "".join(thinking_parts)
            final_tool_calls = [
                tool_call
                for tool_call in accumulated_tool_calls
                if tool_call.get("function", {}).get("name")
            ]

            # ── 第 3 步：无工具调用 → 对话结束 ──
            if not final_tool_calls:
                new_messages.append(
                    Message(
                        role="assistant",
                        timestamp=datetime.now().isoformat(),
                        content=full_reply,
                        reasoning_content=full_thinking or None,
                    )
                )
                yield LoopResult(new_messages=new_messages, pattern_events=pattern_events)
                return

            # ── 第 4 步：有工具调用 → 先记 assistant 消息 ──
            self.context_manager.add(
                {
                    "role": "assistant",
                    "content": full_reply or None,
                    "reasoning_content": full_thinking or None,
                    "tool_calls": final_tool_calls,
                }
            )

            # ── 第 5 步：逐个执行工具，收集结果 ──
            tool_call_infos: list[ToolCallInfo] = []
            async for item in self._execute_tool_calls(final_tool_calls):
                if isinstance(item, ToolExecutionResult):
                    # 终值：记入上下文 + 收集元信息
                    self.context_manager.add(item.message_entry)
                    tool_call_infos.append(item.tool_call_info)
                    if item.pattern_event:
                        pattern_events.append(item.pattern_event)
                    continue
                # 进度事件：直接透传
                yield item

            # ── 第 6 步：构建带 tool_call_info 的 assistant 消息 ──
            new_messages.append(
                Message(
                    role="assistant",
                    timestamp=datetime.now().isoformat(),
                    content=full_reply,
                    tool_calls=tool_call_infos,
                    reasoning_content=full_thinking or None,
                )
            )
        else:
            # max_turns 耗尽时的 fallback
            new_messages.append(
                Message(
                    role="assistant",
                    timestamp=datetime.now().isoformat(),
                    content="已达到最大对话轮次，请简化问题。",
                )
            )

        yield LoopResult(new_messages=new_messages, pattern_events=pattern_events)
