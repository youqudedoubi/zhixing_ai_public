"""mentor_agent：组装 model / context / tools / loop，对外暴露 run()。"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, TYPE_CHECKING

from code.config import api_key
from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry
from code.backend.services.research.mentor_agent.append_context_manager import AppendContextManager
from code.backend.services.research.mentor_agent.prompt.build_messages import build_system_prompt
from code.backend.services.research.mentor_agent.supervisor_loop import SupervisorLoop, EmitFn
from code.backend.services.research.mentor_agent.tools.send_message import make_send_message_tool
from code.backend.services.research.mentor_agent.tools.write_report import make_write_report_tool

if TYPE_CHECKING:
    from code.backend.services.research.analyze_agent.analyze_agent import AnalyzeAgent

_MODEL_KWARGS = {
    "reasoning_effort": "high",
    "extra_body": {"thinking": {"type": "enabled"}},
}


class MentorAgent:
    """制定计划、指导 analyze_agent、把控方向、输出最终报告。"""

    def __init__(
        self,
        allowed_root: Path,
        pattern_text: str,
        report_path: Path,
        emit: EmitFn,
        process_log: list[dict],
        analyze: "AnalyzeAgent | None" = None,
    ):
        self.agent_name = "mentor_agent"

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
        self.registry.register(make_write_report_tool(report_path))

        self.system_prompt = build_system_prompt(self.registry, pattern_text)

        self.loop = SupervisorLoop(
            model=self.model,
            context=self.context.messages,
            registry=self.registry,
            agent_name=self.agent_name,
            emit=emit,
            process_log=process_log,
            subordinate=analyze,
            subordinate_name="analyze_agent",
        )

    def run(self, topic: str) -> str:
        if self.context.is_empty():
            self.context.add({"role": "system", "content": self.system_prompt})
        self.context.add({
            "role": "user",
            "content": f"研究课题：{topic}\n\n请开始制定研究计划并指导团队完成研究。",
        })
        return self.loop.run(max_turns=50)
