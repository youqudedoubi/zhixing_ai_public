def extract_pattern_event(tool_name: str, result: dict) -> dict | None:
    if tool_name != "append_log":
        return None
    payload = result.get("result")
    if not isinstance(payload, dict):
        return None
    event = payload.get("event")
    if not isinstance(event, dict):
        return None
    delta = event.get("delta")
    if delta is None:
        return None
    return {
        "pattern_name": event.get("pattern_name", ""),
        "category": event.get("category", ""),
        "delta": int(delta),
        "timestamp": event.get("timestamp", ""),
    }


def sort_pattern_events(events: list[dict]) -> list[dict]:
    def rank(event: dict) -> int:
        category = event.get("category")
        delta = int(event.get("delta", 0))
        if category == "positive" and delta > 0:
            return 0
        if category == "positive" and delta < 0:
            return 1
        if category == "neutral" and delta > 0:
            return 2
        if category == "neutral" and delta < 0:
            return 3
        if category == "negative" and delta > 0:
            return 4
        if category == "negative" and delta < 0:
            return 5
        return 6

    return sorted(events, key=rank)
