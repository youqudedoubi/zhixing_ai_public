import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from code.backend.services.topic import topic_service
from code.backend.services.chat_agent.chat_service import stream_topic_message

router = APIRouter(prefix="/api/topics", tags=["chat"])


class SendMessagePayload(BaseModel):
    content: str


@router.post("/{topic_id}/messages")
async def send_message(topic_id: str, payload: SendMessagePayload):
    try:
        topic_service.get_topic(topic_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    async def event_stream():
        async for sse_event in stream_topic_message(topic_id, payload.content):
            yield sse_event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
