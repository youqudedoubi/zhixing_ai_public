import subprocess
from pathlib import Path

from code.config import root

DATA_DIR = Path(root).resolve()


def resolve_data_path(filepath: str) -> Path:
    path = (DATA_DIR / filepath).resolve()
    path.relative_to(DATA_DIR)
    return path


def ensure_git_init() -> None:
    git_dir = DATA_DIR / ".git"
    if not git_dir.exists():
        subprocess.run(["git", "init"], cwd=DATA_DIR, check=True, capture_output=True)


def run_git(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", f"safe.directory={DATA_DIR}"] + args,
        cwd=DATA_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **kwargs,
    )
