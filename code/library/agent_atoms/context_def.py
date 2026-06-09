from abc import ABC, abstractmethod
class BaseContextManager(ABC):
    @abstractmethod
    def add(self, message: dict) -> None:
        pass

    @abstractmethod
    def get_messages(self) -> list[dict]:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def is_empty(self)->bool:
        pass
