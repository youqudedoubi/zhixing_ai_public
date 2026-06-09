"""critic_agent：组装 model / context / tools / loop，对外暴露 run()。"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from code.config import api_key
from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry
from code.backend.services.research.critic_agent.append_context_manager import AppendContextManager
from code.backend.services.research.critic_agent.prompt.build_messages import build_system_prompt
from code.backend.services.research.critic_agent.worker_loop import WorkerLoop, EmitFn
from code.backend.services.research.critic_agent.tools.send_message import make_send_message_tool
from code.backend.services.research.critic_agent.tools.read_pattern import make_read_pattern_tool
from code.backend.services.research.critic_agent.tools.read_diary import make_read_diary_tool
from code.backend.services.research.critic_agent.tools.list_pattern import make_list_pattern_tool

_MODEL_KWARGS = {
    "reasoning_effort": "high",
    "extra_body": {"thinking": {"type": "enabled"}},
}


class CriticAgent:
    """建设性质疑 analyze_agent 的分析，帮助校准结论。"""

    def __init__(
        self,
        allowed_root: Path,
        pattern_text: str,
        emit: EmitFn,
        process_log: list[dict],
    ):
        self.agent_name = "critic_agent"

        self.model = BaseModel(
            model_name="deepseek-v4-pro",
            api_key=api_key,
            base_url="https://api.deepseek.com",
            default_generate_kwargs=_MODEL_KWARGS,
        )
        self.context = AppendContextManager()

        self.registry = ToolRegistry()
        self.registry.register(make_send_message_tool(
            agent_name=self.agent_name,
            valid_targets=["analyze_agent"],
            emit=emit,
            process_log=process_log,
        ))
        self.registry.register(make_list_pattern_tool(allowed_root))
        self.registry.register(make_read_pattern_tool(allowed_root))
        self.registry.register(make_read_diary_tool(allowed_root))

        self.system_prompt = build_system_prompt(self.registry, pattern_text)

        self.loop = WorkerLoop(
            model=self.model,
            context=self.context.messages,
            registry=self.registry,
            agent_name=self.agent_name,
            emit=emit,
            process_log=process_log,
            superior_name="analyze_agent",
            peer_name=None,
            peer=None,
        )

    def run(self, question: str) -> str:
        if self.context.is_empty():
            self.context.add({"role": "system", "content": self.system_prompt})
        self.context.add({
            "role": "user",
            "content": f"[来自 analyze_agent]\n{question}",
        })
        return self.loop.run(max_turns=50)
