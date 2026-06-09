from dataclasses import dataclass, field

from code.backend.models.schemas import Message


@dataclass(frozen=True)
class ThinkingStart:
    pass


@dataclass(frozen=True)
class ThinkingToken:
    token: str


@dataclass(frozen=True)
class ThinkingEnd:
    pass


@dataclass(frozen=True)
class TextToken:
    token: str


@dataclass(frozen=True)
class ToolCallStart:
    name: str
    arguments: dict


@dataclass(frozen=True)
class ToolCallResult:
    name: str
    result: str


@dataclass(frozen=True)
class RawSSE:
    """已由外部格式化的 SSE 行（如 research 子 agent 缓冲）。"""
    data: str


@dataclass
class LoopResult:
    new_messages: list[Message] = field(default_factory=list)
    pattern_events: list[dict] = field(default_factory=list)


LoopEvent = (
    ThinkingStart
    | ThinkingToken
    | ThinkingEnd
    | TextToken
    | ToolCallStart
    | ToolCallResult
    | RawSSE
)
