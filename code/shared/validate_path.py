from pathlib import Path


def validate_path(path: str, allowed_root: Path) -> Path:
    resolved = (allowed_root / path).resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError:
        raise ValueError(f"Path outside allowed root: {path}")
    return resolved
