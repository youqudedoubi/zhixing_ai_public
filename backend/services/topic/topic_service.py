import json
import uuid
import re
from datetime import datetime
from pathlib import Path
from code.backend.models.schemas import Topic, TopicSummary, Message
from code.backend.services.workspace.checkpoint import restore_workspace_to_checkpoint

# backend 内部数据目录，与用户数据（zhixing_data）分离
TOPICS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "topics"


def _ensure_dir():
    TOPICS_DIR.mkdir(parents=True, exist_ok=True)


def _topic_path(topic_id: str) -> Path:
    return TOPICS_DIR / f"{topic_id}.json"


def _read_topic(topic_id: str) -> Topic:
    path = _topic_path(topic_id)
    if not path.exists():
        raise FileNotFoundError(f"话题 {topic_id} 不存在")
    return Topic(**json.loads(path.read_text(encoding="utf-8")))


def _write_topic(topic: Topic):
    path = _topic_path(topic.id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(topic.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _count_topic_number() -> int:
    _ensure_dir()
    pattern = re.compile(r"^话题(\d+)$")
    nums = set()
    for f in TOPICS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            m = pattern.match(data.get("topic_name", ""))
            if m:
                nums.add(int(m.group(1)))
        except Exception:
            pass
    n = 1
    while n in nums:
        n += 1
    return n


def list_topics() -> list[TopicSummary]:
    _ensure_dir()
    result = []
    for f in sorted(TOPICS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            result.append(TopicSummary(
                id=data["id"],
                topic_name=data["topic_name"],
                created_at=data["created_at"],
                message_count=len(data.get("messages", [])),
            ))
        except Exception:
            continue
    return result


def get_topic(topic_id: str) -> Topic:
    return _read_topic(topic_id)


def create_topic(name: str | None = None) -> Topic:
    _ensure_dir()
    topic = Topic(
        id=uuid.uuid4().hex[:12],
        topic_name=name or f"话题{_count_topic_number()}",
        created_at=datetime.now().isoformat(),
        messages=[],
    )
    _write_topic(topic)
    return topic


def rename_topic(topic_id: str, new_name: str) -> Topic:
    topic = _read_topic(topic_id)
    topic.topic_name = new_name
    _write_topic(topic)
    return topic


def delete_topic(topic_id: str):
    path = _topic_path(topic_id)
    if not path.exists():
        raise FileNotFoundError(f"话题 {topic_id} 不存在")
    path.unlink()


def add_message(topic_id: str, message: Message) -> Topic:
    topic = _read_topic(topic_id)
    topic.messages.append(message)
    _write_topic(topic)
    return topic


def add_messages(topic_id: str, messages: list[Message]) -> Topic:
    topic = _read_topic(topic_id)
    topic.messages.extend(messages)
    _write_topic(topic)
    return topic


def rollback_conversation(topic_id: str, message_index: int) -> Topic:
    topic = _read_topic(topic_id)
    if message_index < 0 or message_index >= len(topic.messages):
        raise IndexError(f"消息索引 {message_index} 不存在")
    if topic.messages[message_index].role != "user":
        raise ValueError("只能回退到用户消息")

    topic.messages = topic.messages[:message_index]
    _write_topic(topic)
    return topic


def rollback_files(topic_id: str, message_index: int):
    topic = _read_topic(topic_id)
    if message_index < 0 or message_index >= len(topic.messages):
        raise IndexError(f"消息索引 {message_index} 不存在")
    target = topic.messages[message_index]
    if target.role != "user":
        raise ValueError("只能回退到用户消息")
    if not target.checkpoint_sha:
        raise ValueError("该消息没有可用的文件快照")

    restore_workspace_to_checkpoint(target.checkpoint_sha)


def rollback_conversation_and_files(topic_id: str, message_index: int) -> Topic:
    rollback_files(topic_id, message_index)
    return rollback_conversation(topic_id, message_index)


def branch_topic(topic_id: str, from_message_index: int) -> Topic:
    topic = _read_topic(topic_id)
    base_name = topic.topic_name
    _ensure_dir()
    suffix_pattern = re.compile(rf"^{re.escape(base_name)}\((\d+)\)$")
    existing_nums = set()
    for f in TOPICS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            m = suffix_pattern.match(data.get("topic_name", ""))
            if m:
                existing_nums.add(int(m.group(1)))
        except Exception:
            pass
    n = 1
    while n in existing_nums:
        n += 1
    new_topic = Topic(
        id=uuid.uuid4().hex[:12],
        topic_name=f"{base_name}({n})",
        created_at=datetime.now().isoformat(),
        messages=topic.messages[:from_message_index + 1],
    )
    _write_topic(new_topic)
    return new_topic
