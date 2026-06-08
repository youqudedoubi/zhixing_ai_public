
from code.library.agent_atoms.llm import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry
from code.library.agent_atoms.context_def import BaseContextManager

class BaseLoop:
    def __init__(
            self,
            model: BaseModel,
            tool_registry: ToolRegistry,
            context_manager: BaseContextManager
    ):
        self.model = model
        self.context_manager = context_manager
        self.tool_registry = tool_registry

    def run(self, message, max_turns) -> str:
        pass


