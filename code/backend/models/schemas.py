from pydantic import BaseModel
from typing import Optional


class ToolCallInfo(BaseModel):
    tool_name: str
    arguments: dict
    result: Optional[str] = None
    call_id: Optional[str] = None


class ModifiedFile(BaseModel):
    path: str
    change_type: str  # "created" | "modified" | "deleted"
    pre_content: str = ""
    post_content: str = ""


class Message(BaseModel):
    role: str  # "user" | "assistant" | "action"
    timestamp: str  # ISO 8601
    content: str = ""
    checkpoint_sha: Optional[str] = None
    tool_calls: Optional[list[ToolCallInfo]] = None
    reasoning_content: Optional[str] = None
    # action 消息专用字段
    action_type: Optional[str] = None    # e.g. "file_change"
    action_status: Optional[str] = None  # e.g. "completed"
    action_data: Optional[dict] = None   # action-type-specific payload


class Topic(BaseModel):
    id: str
    topic_name: str
    created_at: str  # ISO 8601
    messages: list[Message] = []


class TopicSummary(BaseModel):
    id: str
    topic_name: str
    created_at: str
    message_count: int


# ── Simulation ──────────────────────────────────────────────────────────────

class SimulationNode(BaseModel):
    id: str
    pattern_name: str
    phase: str  # "第一反应" | "次生思维" | "强化思维"
    content: str
    parent_id: Optional[str] = None
    children: list["SimulationNode"] = []


class SimulationResult(BaseModel):
    id: str
    name: str
    config_name: str
    situation: str
    max_branches: int
    max_steps: int
    alpha: float
    created_at: str
    root: Optional[SimulationNode] = None


class SimulationSession(BaseModel):
    id: str
    name: str
    created_at: str
    result_id: Optional[str] = None


class PatternItem(BaseModel):
    rel_path: str   # relative to config dir, e.g. "positive/FOMO情绪.md"
    name: str
    category: str   # "positive" | "negative" | "neutral"
    intensity: float
