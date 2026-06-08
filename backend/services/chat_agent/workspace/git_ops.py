from code.backend.services.chat_agent.workspace.git_repository import (
    ensure_git_init,
    resolve_data_path,
    run_git,
)


def revert_file(filepath: str) -> None:
    ensure_git_init()
    full_path = resolve_data_path(filepath)
    tracked = run_git(["ls-files", "--error-unmatch", filepath])
    if tracked.returncode == 0:
        run_git(["checkout", "HEAD", "--", filepath], check=True)
    elif full_path.exists() and full_path.is_file():
        full_path.unlink()


def commit_all() -> None:
    ensure_git_init()
    run_git(["add", "-A"], check=True)
    if run_git(["status", "--porcelain"]).stdout.strip():
        run_git(["commit", "-m", "chat-agent-keep-all"], check=True)


def commit_files(filepaths: list[str]) -> None:
    ensure_git_init()
    paths = list(dict.fromkeys(filepaths))
    if not paths:
        return
    for filepath in paths:
        resolve_data_path(filepath)
    run_git(["add", "--"] + paths, check=True)
    status = run_git(["status", "--porcelain", "--"] + paths)
    if status.stdout.strip():
        run_git(["commit", "-m", "chat-agent-keep-files"], check=True)


def stage_file(filepath: str) -> None:
    ensure_git_init()
    resolve_data_path(filepath)
    run_git(["add", filepath], check=True)
    status = run_git(["status", "--porcelain", "--", filepath])
    if status.stdout.strip():
        run_git(["commit", "-m", f"chat-agent-save: {filepath}"], check=True)
