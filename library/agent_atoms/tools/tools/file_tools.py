from pathlib import Path
from code.library.agent_atoms.tools.tool_def import Tool
from code.shared.validate_path import validate_path

def _read_file(path: str, allowed_root: Path, offset: int | None = None, limit: int | None = None) -> str:
    try:
        p = validate_path(path, allowed_root)
    except ValueError as e:
        return str(e)
    if not p.is_file():
        return f"路径不是文件或不存在：{path}"
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if offset is not None or limit is not None:
        start = (offset or 1) - 1
        start = max(0, start)
        end = start + (limit or len(lines)) if limit else len(lines)
        lines = lines[start:end]
    return "\n".join(lines)


def _write(path: str, allowed_root: Path, contents: str) -> str:
    try:
        p = validate_path(path, allowed_root)
    except ValueError as e:
        return str(e)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(contents, encoding="utf-8")
    return f"已写入 {path}"


def _search_replace(
    path: str,
    allowed_root: Path,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> str:
    try:
        p = validate_path(path, allowed_root)
    except ValueError as e:
        return str(e)
    if not p.is_file():
        return f"路径不是文件或不存在：{path}"
    text = p.read_text(encoding="utf-8", errors="replace")
    if replace_all:
        count = text.count(old_string)
        new_text = text.replace(old_string, new_string)
    else:
        if old_string not in text:
            return f"未找到匹配的 old_string"
        count = 1
        new_text = text.replace(old_string, new_string, 1)
    p.write_text(new_text, encoding="utf-8")
    return f"已替换 {count} 处"


def make_read_file_tool(allowed_root: Path) -> Tool:
    def fn(path: str, offset: int | None = None, limit: int | None = None) -> str:
        return _read_file(path, allowed_root, offset, limit)

    return Tool(
        name="read_file_plain_text",
        description="读取文件内容。可指定 offset（起始行，从1开始）、limit（行数）进行分页。",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "offset": {"type": "integer", "description": "起始行号，从1开始"},
                "limit": {"type": "integer", "description": "读取行数"},
            },
            "required": ["path"],
        },
        fn=fn,
    )


def make_write_tool(allowed_root: Path) -> Tool:
    def fn(path: str, contents: str) -> str:
        return _write(path, allowed_root, contents)

    return Tool(
        name="write",
        description="新建文件或覆盖整个文件。会完全替换原内容，适合新建或整文件重写。",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "contents": {"type": "string", "description": "文件内容"},
            },
            "required": ["path", "contents"],
        },
        fn=fn,
    )


def make_search_replace_tool(allowed_root: Path) -> Tool:
    def fn(
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
        return _search_replace(path, allowed_root, old_string, new_string, replace_all)

    return Tool(
        name="search_replace_plain_text",
        description="在文件中做精确字符串替换。old_string 必须与原文完全一致（含空格、缩进），适合局部修改。",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "old_string": {"type": "string", "description": "要替换的原文"},
                "new_string": {"type": "string", "description": "新内容"},
                "replace_all": {"type": "boolean", "description": "是否替换全部出现", "default": False},
            },
            "required": ["path", "old_string", "new_string"],
        },
        fn=fn,
    )
