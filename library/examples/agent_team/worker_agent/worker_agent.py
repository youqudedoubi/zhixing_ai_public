"""worker_agent：组装 model / context / tools / loop，对外暴露 run()。"""
from pathlib import Path
from typing import Callable

from code.config import api_key
from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry
from code.library.examples.agent_team.worker_agent.append_context_manager import AppendContextManager
from code.library.examples.agent_team.worker_agent.prompt.build_messages import build_system_prompt
from code.library.examples.agent_team.worker_agent.worker_loop import WorkerLoop
from code.library.examples.agent_team.worker_agent.tools.send_message import make_send_message_tool
from code.library.examples.agent_team.worker_agent.tools.get_time import make_get_time_tool

EmitFn = Callable[[str, str, str], None]  # (agent_name, content, msg_type)


class WorkerAgent:
    """接收 boss 的任务，使用工具执行，完成后汇报。"""

    def __init__(
        self,
        emit: EmitFn,
        process_log: list[dict],
    ):
        self.agent_name = "worker_agent"

        self.model = BaseModel(
            model_name="deepseek-v4-pro",
            api_key=api_key,
            base_url="https://api.deepseek.com",
            default_generate_kwargs={
                "reasoning_effort": "high",
                "extra_body": {"thinking": {"type": "enabled"}},
            },
        )
        self.context = AppendContextManager()

        self.registry = ToolRegistry()
        self.registry.register(make_send_message_tool(
            agent_name=self.agent_name,
            valid_targets=["boss_agent"],
            emit=emit,
            process_log=process_log,
        ))
        self.registry.register(make_get_time_tool())

        self.system_prompt = build_system_prompt(self.registry)

        self.loop = WorkerLoop(
            model=self.model,
            context=self.context.messages,
            registry=self.registry,
            agent_name=self.agent_name,
            emit=emit,
            process_log=process_log,
            superior_name="boss_agent",
        )

    def run(self, task: str) -> str:
        if self.context.is_empty():
            self.context.add({"role": "system", "content": self.system_prompt})
        self.context.add({
            "role": "user",
            "content": f"[来自 boss_agent]\n{task}",
        })
        return self.loop.run(max_turns=50)
