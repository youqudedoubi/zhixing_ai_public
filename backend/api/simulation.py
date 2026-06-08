"""Simulation API endpoints."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel as PydanticModel

from code.config import root
from code.backend.models.schemas import SimulationSession
from code.backend.services.simulation import config_service, result_service
from code.backend.services.simulation.simulation_engine import run_simulation

router = APIRouter(prefix="/api/simulation", tags=["simulation"])

_ROOT = Path(root).resolve()
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _sse(event_type: str, data: dict | None = None) -> str:
    payload = {"type": event_type}
    if data:
        payload.update(data)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ── Config endpoints ──────────────────────────────────────────────────────────

@router.get("/configs")
def list_configs():
    return {"configs": config_service.list_configs(_ROOT)}


@router.post("/configs/default/update")
def update_default_config():
    """SSE stream: generates thought flows for all patterns in analysis/pattern/."""
    import queue
    import threading

    q: queue.Queue = queue.Queue()

    def emit(s: str) -> None:
        q.put(s)

    def worker():
        try:
            config_service.update_default_config(_ROOT, emit=emit)
        except Exception as e:
            q.put(_sse("error", {"message": str(e)}))
        finally:
            q.put(None)  # sentinel

    threading.Thread(target=worker, daemon=True).start()

    def gen():
        while True:
            item = q.get()
            if item is None:
                yield _sse("done", {"message": "默认配置更新完成"})
                break
            yield item

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


class RenameConfigPayload(PydanticModel):
    new_name: str


@router.post("/configs")
def create_config():
    new_name = config_service.create_config(_ROOT)
    return {"config_name": new_name}


@router.put("/configs/{config_name}/rename")
def rename_config(config_name: str, payload: RenameConfigPayload):
    try:
        config_service.rename_config(_ROOT, config_name, payload.new_name)
    except (FileNotFoundError, ValueError) as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    return {"config_name": payload.new_name}


@router.get("/configs/{config_name}/patterns")
def list_patterns(config_name: str):
    patterns = config_service.list_patterns(_ROOT, config_name)
    return {"patterns": [p.model_dump() for p in patterns]}


class UpdateIntensityPayload(PydanticModel):
    rel_path: str
    intensity: float


@router.put("/configs/{config_name}/patterns/intensity")
def update_intensity(config_name: str, payload: UpdateIntensityPayload):
    config_service.update_pattern_intensity(_ROOT, config_name, payload.rel_path, payload.intensity)
    return {"success": True}


# ── Simulation run ────────────────────────────────────────────────────────────

class RunSimulationPayload(PydanticModel):
    session_id: str
    config_name: str
    situation: str
    max_branches: int = 2
    max_steps: int = 3
    alpha: float = 0.6
    seed: int | None = None


@router.post("/run")
def run_simulation_endpoint(payload: RunSimulationPayload):
    import queue
    import threading

    q: queue.Queue = queue.Queue()

    def emit(s: str) -> None:
        q.put(s)

    def worker():
        try:
            patterns = config_service.list_patterns(_ROOT, payload.config_name)
            result = run_simulation(
                situation=payload.situation,
                config_name=payload.config_name,
                patterns=patterns,
                root=_ROOT,
                max_branches=payload.max_branches,
                max_steps=payload.max_steps,
                alpha=payload.alpha,
                emit=emit,
                seed=payload.seed,
            )
            result_service.save_result(_ROOT, result)
            result_service.attach_result_to_session(_DATA_DIR, payload.session_id, result.id)
        except Exception as e:
            q.put(_sse("error", {"message": str(e)}))
        finally:
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def gen():
        while True:
            item = q.get()
            if item is None:
                break
            yield item

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


# ── Session endpoints ─────────────────────────────────────────────────────────

@router.get("/sessions")
def list_sessions():
    sessions = result_service.list_sessions(_DATA_DIR)
    return {"sessions": [s.model_dump() for s in sessions]}


class CreateSessionPayload(PydanticModel):
    name: str


@router.post("/sessions")
def create_session(payload: CreateSessionPayload):
    session = result_service.create_session(_DATA_DIR, payload.name)
    return session.model_dump()


class RenameSessionPayload(PydanticModel):
    name: str


@router.put("/sessions/{session_id}/rename")
def rename_session(session_id: str, payload: RenameSessionPayload):
    session = result_service.rename_session(_DATA_DIR, session_id, payload.name)
    return session.model_dump()


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    result_service.delete_session(_DATA_DIR, session_id, root=_ROOT)
    return {"success": True}


# ── Result endpoints ──────────────────────────────────────────────────────────

@router.get("/results/{result_id}")
def get_result(result_id: str):
    result = result_service.get_result(_ROOT, result_id)
    return result.model_dump()
