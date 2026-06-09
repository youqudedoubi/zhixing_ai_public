from code.library.agent_atoms.llm import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry
from code.library.agent_atoms.context_def import BaseContextManager
from code.library.agent_atoms.loop_def import BaseLoop
# 这里只是做示例、参照，不使用基类，所以不强制要求相同
# 例如，如果希望用户能自主定义用哪个模型，那这里model应由外界应是init传入参数
class BaseAgent:
    def __init__(
        self,
    ):
        self.model : BaseModel
        self.context_manager : BaseContextManager
        self.tool_registry : ToolRegistry
        self.loop : BaseLoop

    def build_system_prompt(self)  -> str:
        pass

    def build_user_prompt(self)  -> str:
        pass

    def run(self,message):
        pass


