"""Simulation session and result persistence."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from code.backend.models.schemas import SimulationResult, SimulationSession
from code.backend.services.simulation import SIM_DIR, RESULT_DIR, SESSIONS_FILE


def _sessions_path(data_dir: Path) -> Path:
    return data_dir / SESSIONS_FILE


def _load_sessions(data_dir: Path) -> list[SimulationSession]:
    p = _sessions_path(data_dir)
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return [SimulationSession(**s) for s in raw]
    except Exception:
        import traceback
        import sys
        print(f"[simulation] 警告：会话文件已损坏 {p}，返回空列表", file=sys.stderr)
        traceback.print_exc()
        return []


def _save_sessions(data_dir: Path, sessions: list[SimulationSession]) -> None:
    """原子写入：先写入 .tmp，再重命名，防止写入过程中崩溃导致文件损坏。"""
    data_dir.mkdir(parents=True, exist_ok=True)
    path = _sessions_path(data_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps([s.model_dump() for s in sessions], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)  # 在大多数文件系统上是原子的


def list_sessions(data_dir: Path) -> list[SimulationSession]:
    return _load_sessions(data_dir)


def create_session(data_dir: Path, name: str) -> SimulationSession:
    sessions = _load_sessions(data_dir)
    session = SimulationSession(
        id=uuid.uuid4().hex[:12],
        name=name,
        created_at=datetime.now().isoformat(),
    )
    sessions.append(session)
    _save_sessions(data_dir, sessions)
    return session


def rename_session(data_dir: Path, session_id: str, name: str) -> SimulationSession:
    sessions = _load_sessions(data_dir)
    for s in sessions:
        if s.id == session_id:
            s.name = name
            _save_sessions(data_dir, sessions)
            return s
    raise FileNotFoundError(f"Session not found: {session_id}")


def delete_session(data_dir: Path, session_id: str, root: Path) -> None:
    """移除会话记录并删除关联的结果 JSON 文件。"""
    sessions = _load_sessions(data_dir)
    target = next((s for s in sessions if s.id == session_id), None)
    if target and target.result_id:
        result_file = root / SIM_DIR / RESULT_DIR / f"{target.result_id}.json"
        if result_file.exists():
            result_file.unlink()
    sessions = [s for s in sessions if s.id != session_id]
    _save_sessions(data_dir, sessions)


def save_result(root: Path, result: SimulationResult) -> str:
    """持久化结果 JSON。返回 result_id。"""
    result_dir = root / SIM_DIR / RESULT_DIR
    result_dir.mkdir(parents=True, exist_ok=True)
    path = result_dir / f"{result.id}.json"
    path.write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result.id


def attach_result_to_session(data_dir: Path, session_id: str, result_id: str) -> None:
    sessions = _load_sessions(data_dir)
    for s in sessions:
        if s.id == session_id:
            s.result_id = result_id
            _save_sessions(data_dir, sessions)
            return
    raise FileNotFoundError(f"Session not found: {session_id}")


def get_result(root: Path, result_id: str) -> SimulationResult:
    path = root / SIM_DIR / RESULT_DIR / f"{result_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Result not found: {result_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return SimulationResult(**data)
