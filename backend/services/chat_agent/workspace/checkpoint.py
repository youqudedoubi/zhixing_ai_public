from code.backend.services.chat_agent.workspace.git_repository import (
    DATA_DIR,
    ensure_git_init,
    resolve_data_path,
    run_git,
)


def create_checkpoint() -> str:
    ensure_git_init()
    run_git(["add", "-A"], check=True)
    run_git(["commit", "--allow-empty", "-m", "chat-agent-checkpoint"], check=True)
    return run_git(["rev-parse", "HEAD"], check=True).stdout.strip()


def get_modified_files(since_sha: str) -> list[dict]:
    ensure_git_init()
    result = run_git(["status", "--porcelain", "-z"])
    if result.returncode != 0:
        return []

    files = []
    for line in result.stdout.split("\0"):
        if not line or len(line) < 3:
            continue
        xy = line[:2]
        filepath = line[3:].strip()

        if xy == "??":
            if filepath.endswith("/"):
                dir_path = resolve_data_path(filepath.rstrip("/"))
                if dir_path.is_dir():
                    for file_path in sorted(dir_path.rglob("*")):
                        if file_path.is_file():
                            rel = str(file_path.relative_to(DATA_DIR)).replace("\\", "/")
                            try:
                                content = file_path.read_text(encoding="utf-8", errors="replace")[:10000]
                            except Exception:
                                content = ""
                            files.append({"path": rel, "change_type": "created", "pre_content": "", "post_content": content})
                continue
            change_type = "created"
        elif xy == " D" or xy[1] == "D":
            change_type = "deleted"
        elif xy[1] == "M":
            change_type = "modified"
        elif xy[0] == "A":
            change_type = "created"
        else:
            continue

        pre_content = ""
        post_content = ""
        full_path = resolve_data_path(filepath)
        if change_type != "deleted" and full_path.exists():
            try:
                post_content = full_path.read_text(encoding="utf-8", errors="replace")[:10000]
            except Exception:
                pass
        if change_type != "created":
            try:
                pre_content = run_git(["show", f"{since_sha}:{filepath}"]).stdout[:10000]
            except Exception:
                pass

        files.append({
            "path": filepath,
            "change_type": change_type,
            "pre_content": pre_content,
            "post_content": post_content,
        })
    return files


def get_file_diff(filepath: str, since_sha: str) -> str:
    result = run_git(["diff", since_sha, "--", filepath])
    return result.stdout


def _list_files_in_checkpoint(checkpoint_sha: str) -> set[str]:
    # -z: NUL-terminated output, avoids git's double-quote + octal escaping
    # for paths with non-ASCII characters (e.g. Chinese filenames).
    result = run_git(["ls-tree", "-r", "--name-only", "-z", checkpoint_sha], check=True)
    return {line for line in result.stdout.split("\0") if line.strip()}


def restore_workspace_to_checkpoint(checkpoint_sha: str) -> None:
    ensure_git_init()
    checkpoint_files = _list_files_in_checkpoint(checkpoint_sha)
    current_files = {
        str(path.relative_to(DATA_DIR)).replace("\\", "/")
        for path in DATA_DIR.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }

    run_git(["checkout", checkpoint_sha, "--", "."], check=True)

    for relative_path in current_files - checkpoint_files:
        full_path = resolve_data_path(relative_path)
        if full_path.exists() and full_path.is_file():
            full_path.unlink()

    for directory in sorted(
        (path for path in DATA_DIR.rglob("*") if path.is_dir() and ".git" not in path.parts),
        key=lambda item: len(item.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            pass
