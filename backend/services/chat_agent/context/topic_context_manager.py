from datetime import datetime

from code.backend.models.schemas import Message
from code.backend.services.chat_agent.command.registry import CommandMatch
from code.backend.services.chat_agent.prompt.build_messages import build_messages
from code.backend.services.topic import topic_service
from code.library.agent_atoms.context_def import BaseContextManager
from code.library.agent_atoms.skills.skills_loader import SkillHub
from code.library.agent_atoms.tools.tools_loader import ToolHub


class TopicContextManager(BaseContextManager):
    """管理某个话题的对话上下文。"""

    def __init__(self, topic_id: str | None = None):
        self.topic_id = topic_id
        self._messages: list[dict] = []
        self._history_messages: list[Message] = []

    @classmethod
    def ephemeral(
        cls,
        history: list[Message],
        user_text: str,
        system_prompt: str,
        skill_hub: SkillHub,
        tool_hub: ToolHub,
        command_match: CommandMatch | None = None,
    ) -> "TopicContextManager":
        ctx = cls(topic_id=None)
        ctx._history_messages = list(history)
        ctx._messages = build_messages(
            system_prompt=system_prompt,
            history=history,
            user_text=user_text,
            skill_hub=skill_hub,
            tool_hub=tool_hub,
            command_match=command_match,
        )
        return ctx

    def begin_turn(
        self,
        content: str,
        checkpoint_sha: str,
        system_prompt: str,
        skill_hub: SkillHub,
        tool_hub: ToolHub,
        command_match: CommandMatch | None = None,
    ) -> None:
        if self.topic_id:
            self.save_user_message(content, checkpoint_sha)
        self.prepare_turn(
            user_text=content,
            system_prompt=system_prompt,
            skill_hub=skill_hub,
            tool_hub=tool_hub,
            command_match=command_match,
        )

    def save_user_message(self, content: str, checkpoint_sha: str) -> None:
        if not self.topic_id:
            return
        user_msg = Message(
            role="user",
            timestamp=datetime.now().isoformat(),
            content=content,
            checkpoint_sha=checkpoint_sha,
        )
        topic_service.add_message(self.topic_id, user_msg)

    def prepare_turn(
        self,
        user_text: str,
        system_prompt: str,
        skill_hub: SkillHub,
        tool_hub: ToolHub,
        command_match: CommandMatch | None = None,
    ) -> None:
        if self.topic_id:
            topic = topic_service.get_topic(self.topic_id)
            history = topic.messages[:-1]
            self._history_messages = history

        self._messages = build_messages(
            system_prompt=system_prompt,
            history=self._history_messages,
            user_text=user_text,
            skill_hub=skill_hub,
            tool_hub=tool_hub,
            command_match=command_match,
        )

    def add(self, message: dict) -> None:
        self._messages.append(message)

    def get_messages(self) -> list[dict]:
        return list(self._messages)

    def reset(self) -> None:
        self._messages = []
        self._history_messages = []

    def is_empty(self) -> bool:
        return len(self._messages) == 0

    def commit_turn(self, new_messages: list[Message]) -> None:
        if not self.topic_id or not new_messages:
            return
        topic_service.add_messages(self.topic_id, new_messages)
