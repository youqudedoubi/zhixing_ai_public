from fastapi import APIRouter, Query
from pydantic import BaseModel
from code.backend.services.file.file_service import (
    list_dir, read_file, create_file, save_file, rename_file, delete_file, move_file,
)

router = APIRouter(prefix="/api/files", tags=["files"])


class CreatePayload(BaseModel):
    path: str
    is_folder: bool = False


class SavePayload(BaseModel):
    path: str
    content: str


class RenamePayload(BaseModel):
    path: str
    new_name: str


class DeletePayload(BaseModel):
    path: str


class MovePayload(BaseModel):
    src: str
    dst_folder: str


@router.get("/root")
def api_root():
    from code.config import root
    import os
    return {"name": os.path.basename(str(root).rstrip("/\\")), "path": str(root)}


@router.get("/list")
def api_list_dir(path: str = Query(default="", description="相对于root的路径")):
    return list_dir(path)


@router.get("/read")
def api_read_file(path: str = Query(..., description="相对于root的文件路径")):
    return {"content": read_file(path), "path": path}


@router.post("/create")
def api_create_file(payload: CreatePayload):
    return create_file(payload.path, payload.is_folder)


@router.put("/save")
def api_save_file(payload: SavePayload):
    return save_file(payload.path, payload.content)


@router.put("/rename")
def api_rename_file(payload: RenamePayload):
    return rename_file(payload.path, payload.new_name)


@router.delete("/delete")
def api_delete_file(payload: DeletePayload):
    return delete_file(payload.path)


@router.put("/move")
def api_move_file(payload: MovePayload):
    return move_file(payload.src, payload.dst_folder)
