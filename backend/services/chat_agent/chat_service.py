from typing import AsyncGenerator

from code.backend.services.chat_agent.chat_agent import ChatAgent


async def stream_topic_message(topic_id: str, content: str) -> AsyncGenerator[str, None]:
    agent = ChatAgent(topic_id)
    async for event in agent.run(content):
        yield event
