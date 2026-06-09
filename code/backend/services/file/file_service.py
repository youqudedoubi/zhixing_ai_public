from pathlib import Path
from code.config import root

ROOT = Path(root).resolve()


def validate_path(path: str) -> Path:
    resolved = (ROOT / path).resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        raise ValueError(f"路径越权：{path}")
    return resolved


def list_dir(path: str = "") -> list[dict]:
    p = validate_path(path)
    if not p.is_dir():
        raise FileNotFoundError(f"目录不存在：{path}")
    entries = []
    for item in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        entries.append({
            "name": item.name,
            "type": "folder" if item.is_dir() else "file",
            "path": str(item.relative_to(ROOT)).replace("\\", "/"),
        })
    return entries


def read_file(path: str) -> str:
    p = validate_path(path)
    if not p.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")
    return p.read_text(encoding="utf-8", errors="replace")


def create_file(path: str, is_folder: bool = False) -> dict:
    p = validate_path(path)
    if p.exists():
        raise FileExistsError(f"已存在：{path}")
    if is_folder:
        p.mkdir(parents=True)
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("", encoding="utf-8")
    return {
        "name": p.name,
        "type": "folder" if is_folder else "file",
        "path": str(p.relative_to(ROOT)).replace("\\", "/"),
    }


def save_file(path: str, content: str) -> dict:
    p = validate_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"path": str(p.relative_to(ROOT)).replace("\\", "/"), "saved": True}


def rename_file(old_path: str, new_name: str) -> dict:
    # block path separators in new_name to prevent traversal
    if "/" in new_name or "\\" in new_name or ".." in new_name:
        raise ValueError(f"Invalid name: {new_name}")
    p = validate_path(old_path)
    if not p.exists():
        raise FileNotFoundError(f"不存在：{old_path}")
    new_p = p.parent / new_name
    # verify new path is still within ROOT
    validate_path(str(new_p.relative_to(ROOT)).replace("\\", "/"))
    if new_p.exists():
        raise FileExistsError(f"已存在：{new_name}")
    p.rename(new_p)
    return {
        "old_path": str(p.relative_to(ROOT)).replace("\\", "/"),
        "new_path": str(new_p.relative_to(ROOT)).replace("\\", "/"),
        "name": new_name,
    }


def delete_file(path: str) -> dict:
    p = validate_path(path)
    if not p.exists():
        raise FileNotFoundError(f"不存在：{path}")
    if p.is_dir():
        import shutil
        shutil.rmtree(p)
    else:
        p.unlink()
    return {"path": path, "deleted": True}


def move_file(src: str, dst_folder: str) -> dict:
    p = validate_path(src)
    dst_dir = validate_path(dst_folder)
    if not p.exists():
        raise FileNotFoundError(f"不存在：{src}")
    if not dst_dir.is_dir():
        raise FileNotFoundError(f"目标目录不存在：{dst_folder}")
    new_p = dst_dir / p.name
    if new_p.exists():
        raise FileExistsError(f"目标已存在同名文件：{p.name}")
    p.rename(new_p)
    return {
        "old_path": str(p.relative_to(ROOT)).replace("\\", "/"),
        "new_path": str(new_p.relative_to(ROOT)).replace("\\", "/"),
    }
