from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from code.backend.services.topic import topic_service
from code.backend.models.schemas import Topic, TopicSummary

router = APIRouter(prefix="/api/topics", tags=["topics"])


class CreateTopicBody(BaseModel):
    name: str | None = None


class RenameTopicBody(BaseModel):
    new_name: str


class RollbackBody(BaseModel):
    message_index: int


@router.get("")
async def list_topics() -> list[TopicSummary]:
    return topic_service.list_topics()


@router.post("")
async def create_topic(body: CreateTopicBody = CreateTopicBody()) -> Topic:
    return topic_service.create_topic(body.name)


@router.get("/{topic_id}")
async def get_topic(topic_id: str) -> Topic:
    try:
        return topic_service.get_topic(topic_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{topic_id}/rename")
async def rename_topic(topic_id: str, body: RenameTopicBody) -> Topic:
    try:
        return topic_service.rename_topic(topic_id, body.new_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{topic_id}")
async def delete_topic(topic_id: str):
    try:
        topic_service.delete_topic(topic_id)
        return {"ok": True}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{topic_id}/branch")
async def branch_topic(topic_id: str, from_message_index: int) -> Topic:
    try:
        return topic_service.branch_topic(topic_id, from_message_index)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{topic_id}/rollback_conversation")
async def rollback_conversation(topic_id: str, body: RollbackBody) -> Topic:
    try:
        return topic_service.rollback_conversation(topic_id, body.message_index)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IndexError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{topic_id}/rollback_files")
async def rollback_files(topic_id: str, body: RollbackBody):
    try:
        topic_service.rollback_files(topic_id, body.message_index)
        return {"ok": True}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IndexError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{topic_id}/rollback_conversation_and_files")
async def rollback_conversation_and_files(topic_id: str, body: RollbackBody) -> Topic:
    try:
        return topic_service.rollback_conversation_and_files(topic_id, body.message_index)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IndexError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
