from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema object，描述函数参数
    fn: Callable[..., Any]

    def to_openai_schema(self) -> dict:
        """转换为 OpenAI tools 参数格式。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
