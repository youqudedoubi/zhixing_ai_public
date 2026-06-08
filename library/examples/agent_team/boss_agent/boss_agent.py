"""boss_agent：组装 model / context / tools / loop，对外暴露 run()。"""
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from code.config import api_key
from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry
from code.library.examples.agent_team.boss_agent.append_context_manager import AppendContextManager
from code.library.examples.agent_team.boss_agent.prompt.build_messages import build_system_prompt
from code.library.examples.agent_team.boss_agent.supervisor_loop import SupervisorLoop
from code.library.examples.agent_team.boss_agent.tools.send_message import make_send_message_tool

if TYPE_CHECKING:
    from code.library.examples.agent_team.worker_agent.worker_agent import WorkerAgent

EmitFn = Callable[[str, str, str], None]  # (agent_name, content, msg_type)


class BossAgent:
    """接收用户任务，拆解并调度 worker_agent 执行。"""

    def __init__(
        self,
        emit: EmitFn,
        process_log: list[dict],
        worker: "WorkerAgent | None" = None,
    ):
        self.agent_name = "boss_agent"

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
            valid_targets=["worker_agent"],
            emit=emit,
            process_log=process_log,
        ))

        self.system_prompt = build_system_prompt(self.registry)

        self.loop = SupervisorLoop(
            model=self.model,
            context=self.context.messages,
            registry=self.registry,
            agent_name=self.agent_name,
            emit=emit,
            process_log=process_log,
            subordinate=worker,
            subordinate_name="worker_agent",
        )

    def run(self, task: str) -> str:
        if self.context.is_empty():
            self.context.add({"role": "system", "content": self.system_prompt})
        self.context.add({"role": "user", "content": task})
        return self.loop.run(max_turns=50)
