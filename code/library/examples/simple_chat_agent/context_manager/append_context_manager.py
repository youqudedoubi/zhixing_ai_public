from code.library.agent_atoms.context_def import BaseContextManager


class AppendContextManager(BaseContextManager):
    """按顺序追加保存所有消息的 context manager。"""

    def __init__(self):
        self.messages: list[dict] = []

    def add(self, message: dict) -> None:
        self.messages.append(message)

    def get_messages(self) -> list[dict]:
        return list(self.messages)

    def reset(self) -> None:
        self.messages = []

    def is_empty(self) -> bool:
        return len(self.messages) == 0
