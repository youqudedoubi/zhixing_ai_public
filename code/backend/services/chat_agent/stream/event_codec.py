from typing import AsyncGenerator

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
from code.backend.services.chat_agent.stream.sse import sse


def loop_event_to_sse(event: LoopEvent) -> str:
    if isinstance(event, ThinkingStart):
        return sse("thinking_start")
    if isinstance(event, ThinkingToken):
        return sse("thinking_token", {"token": event.token})
    if isinstance(event, ThinkingEnd):
        return sse("thinking_end")
    if isinstance(event, TextToken):
        return sse("text_token", {"token": event.token})
    if isinstance(event, ToolCallStart):
        return sse("tool_call", {"name": event.name, "arguments": event.arguments})
    if isinstance(event, ToolCallResult):
        return sse("tool_result", {"name": event.name, "result": event.result})
    if isinstance(event, RawSSE):
        return event.data
    raise TypeError(f"Unknown loop event: {type(event)!r}")


async def stream_loop_events(
    loop_events: AsyncGenerator[LoopEvent | LoopResult, None],
) -> AsyncGenerator[str | LoopResult, None]:
    async for item in loop_events:
        if isinstance(item, LoopResult):
            yield item
            continue
        yield loop_event_to_sse(item)
