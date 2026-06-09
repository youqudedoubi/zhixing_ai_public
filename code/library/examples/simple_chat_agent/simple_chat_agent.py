from pathlib import Path

from code.config import api_key
from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.skills.skills_loader import SkillHub, SkillRegistry, get_skill_root
from code.library.agent_atoms.tools.registry import ToolRegistry
from code.library.agent_atoms.tools.tools.file_tools import make_read_file_tool
from code.library.agent_atoms.tools.tools.skill_tool import make_load_skill_tool
from code.library.examples.simple_chat_agent.context_manager.append_context_manager import (
    AppendContextManager,
)
from code.library.examples.simple_chat_agent.loop.tool_call_loop import ToolCallLoop
from code.library.examples.simple_chat_agent.prompt.build_messages import (
    build_system_prompt,
    build_user_message,
)

# 本文档只是一份示例，不必强行一样
# 实际开发中推荐每个agent独立配置tools,loop等，允许重复，不要过早抽象、共用

default_generate_kwargs = {
    "stream": False,
    "reasoning_effort": "max",
    "extra_body": {"thinking": {"type": "enabled"}},
}


def get_deepseek_v4_pro():
    model = BaseModel(
        model_name="deepseek-v4-pro",
        api_key=api_key,
        base_url="https://api.deepseek.com",
        default_generate_kwargs=default_generate_kwargs,
    )
    return model


class SimpleChatAgent:
    def __init__(
        self,
    ):
        self.model = get_deepseek_v4_pro()
        self.context_manager = AppendContextManager()
        self.tool_registry = ToolRegistry()
        self.tool_registry.register(make_read_file_tool(allowed_root=Path.cwd()))

        default_skill_root = Path(__file__).resolve().parent / "skills"
        self.skill_roots = [get_skill_root(), default_skill_root]
        self.skill_names = ["say_hello"]
        self.skill_hub = SkillHub(roots=self.skill_roots)
        self.skill_registry = SkillRegistry(self.skill_hub)
        self.skill_registry.register(self.skill_names or [])
        self.tool_registry.register(make_load_skill_tool(self.skill_registry))

        self.loop = ToolCallLoop(self.model, self.context_manager, self.tool_registry)

    def build_system_prompt(self) -> str:
        system_prompt = build_system_prompt(
            tool_registry=self.tool_registry,
            skill_registry=self.skill_registry,
            root_path=Path.cwd(),
        )
        print(system_prompt)
        return system_prompt

    def build_user_prompt(self, content: str) -> str:
        # 示例中附加一条简单指令，演示 build_user_message 的用法
        return build_user_message(content + "使用say_hello skill")

    def run(self, message) -> str:
        if self.context_manager.is_empty():
            system_prompt = self.build_system_prompt()
            self.context_manager.add({"role": "system", "content": system_prompt})
        message = self.build_user_prompt(message)
        print(message)
        return self.loop.run(message)


if __name__ == "__main__":
    agent = SimpleChatAgent()
    print(
        agent.run(
            r"（1）当前根目录是什么？（2）阅读F:\share\项目\知行AI_2\code\library\examples\simple_chat_agent\context_manager\append_context_manager.py(3)向我打个招呼"
        )
    )
