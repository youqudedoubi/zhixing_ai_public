import re
from pathlib import Path
from typing import Any

from code.library.agent_atoms.tools.tool_def import Tool
from code.shared.validate_path import validate_path

PATTERN_CATEGORIES = ("positive", "negative", "neutral")


def _pattern_root(allowed_root: Path) -> Path:
    return allowed_root / "analysis" / "pattern"


def _ensure_pattern_dirs(allowed_root: Path) -> None:
    root = _pattern_root(allowed_root)
    for category in PATTERN_CATEGORIES:
        (root / category).mkdir(parents=True, exist_ok=True)


def _parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end].strip()
    result: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def _list_pattern(allowed_root: Path) -> str:
    _ensure_pattern_dirs(allowed_root)
    lines: list[str] = []
    root = _pattern_root(allowed_root)
    for category in PATTERN_CATEGORIES:
        lines.append(f"## {category}")
        category_dir = root / category
        entries: list[tuple[str, str]] = []
        for pattern_dir in sorted(category_dir.iterdir(), key=lambda x: x.name):
            if not pattern_dir.is_dir():
                continue
            card = pattern_dir / "pattern.md"
            if not card.exists():
                continue
            content = card.read_text(encoding="utf-8", errors="replace")
            frontmatter = _parse_frontmatter(content)
            name = frontmatter.get("name", pattern_dir.name)
            desc = frontmatter.get("description", "")
            entries.append((name, desc))
        if not entries:
            lines.append("- (empty)")
            continue
        for name, desc in entries:
            lines.append(f"- {name} : {desc}")
    return "\n".join(lines)


def _parse_delta_from_content(content: str) -> int | None:
    m = re.search(r"分值变动[：:]\s*([+-]?\d+)", content)
    if m:
        return int(m.group(1))
    return None


def _append_log(allowed_root: Path, path: str, content: str) -> dict[str, Any]:
    target = validate_path(path, allowed_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    previous = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
    target.write_text(previous + content.rstrip("\n") + "\n\n", encoding="utf-8")

    delta = _parse_delta_from_content(content)
    parts = Path(path).parts
    category = parts[2] if len(parts) >= 4 else ""
    pattern_name = parts[3] if len(parts) >= 4 else ""

    return {
        "success": True,
        "event": {
            "pattern_name": pattern_name,
            "category": category,
            "delta": delta,
        },
    }


def make_list_pattern_tool(allowed_root: Path) -> Tool:
    def fn() -> str:
        return _list_pattern(allowed_root)

    return Tool(
        name="list_pattern",
        description="List all patterns in analysis/pattern grouped by category.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=fn,
    )


def make_append_log_tool(allowed_root: Path) -> Tool:
    def fn(path: str, content: str) -> dict[str, Any]:
        return _append_log(allowed_root=allowed_root, path=path, content=content)

    return Tool(
        name="append_log",
        description="Append a score-change entry to a pattern log.md. Creates the file if it doesn't exist.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to log.md, e.g. analysis/pattern/negative/午后情绪低落/log.md"},
                "content": {"type": "string", "description": "The log entry text to append."},
            },
            "required": ["path", "content"],
        },
        fn=fn,
    )
