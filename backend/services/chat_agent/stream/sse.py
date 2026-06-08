import json


def sse(event_type: str, data: dict | None = None) -> str:
    payload = {"type": event_type}
    if data:
        payload.update(data)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
