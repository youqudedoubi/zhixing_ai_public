from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator

from code.config import api_key
from code.backend.services.chat_agent.command import (
    CommandDefinition,
    CommandHub,
    CommandRegistry,
    parse_command_match,
)
from code.backend.services.chat_agent.prompt.build_messages import (
    ALLOWED_ROOT,
    build_system_prompt,
    resolve_tools,
)
from code.backend.services.chat_agent.context.topic_context_manager import TopicContextManager
from code.backend.services.chat_agent.loop.events import LoopResult
from code.backend.services.chat_agent.loop.tool_call_loop import ToolCallLoop
from code.backend.services.chat_agent.post_turn.finalize import (
    append_action_messages,
    collect_modified_files,
)

from code.backend.services.chat_agent.stream.event_codec import stream_loop_events
from code.backend.services.chat_agent.stream.sse import sse
from code.backend.services.chat_agent.tools import make_get_time_tool, make_list_pattern_tool
from code.backend.services.chat_agent.tools.pattern_tools import make_append_log_tool
from code.backend.services.workspace.checkpoint import create_checkpoint
from code.backend.services.chat_agent.tools.research import make_research_tool
from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.skills.skills_loader import SkillHub, SkillRegistry
from code.library.agent_atoms.tools.tools_loader import ToolHub, ToolRegistry
from code.library.agent_atoms.tools.tools.file_tools import (
    make_read_file_tool,
    make_search_replace_tool,
    make_write_tool,
)
from code.library.agent_atoms.tools.tools.skill_tool import make_load_skill_tool

_BASE_TOOL_NAMES = [
    "read_file_plain_text",
    "write",
    "search_replace_plain_text",
    "list_pattern",
    "get_time",
    "load_skill",
]

_BASE_SKILL_NAMES: list[str] = []

_COMMANDS: dict[str, CommandDefinition] = {
    "/hello": CommandDefinition("/hello", ("say_hello",), ()),
    "/update": CommandDefinition("/update", ("pattern_recognition",), ("append_log",)),
    "/research": CommandDefinition("/research", (), ("research",)),
    "/change": CommandDefinition("/change", ("change",), ()),
}


@dataclass(frozen=True)
class AgentComponents:
    """ChatAgent 依赖的所有组件，由 _init_components 一次性构建。

    用 dataclass 而非裸元组承载返回值：按名字访问，不怕加字段、不怕调顺序。
    """

    model: BaseModel
    tool_hub: ToolHub
    tool_registry: ToolRegistry
    skill_hub: SkillHub
    skill_registry: SkillRegistry
    command_hub: CommandHub
    command_registry: CommandRegistry


class ChatAgent:
    """主对话 Agent：组装 model / tools / skills / command / context / loop，对外暴露 run()。

    context 和 loop 是"每轮重建"的——见 _setup_turn()。
    """

    def __init__(self, topic_id: str):
        self.topic_id = topic_id
        comps = self._init_components()
        self.model = comps.model
        self.tool_hub = comps.tool_hub
        self.tool_registry = comps.tool_registry
        self.skill_hub = comps.skill_hub
        self.skill_registry = comps.skill_registry
        self.command_hub = comps.command_hub
        self.command_registry = comps.command_registry
        # context 和 loop 在 _setup_turn() 中按轮次创建

    @classmethod
    def _init_components(cls) -> AgentComponents:
        model = BaseModel(
            model_name="deepseek-v4-pro",
            api_key=api_key,
            base_url="https://api.deepseek.com",
            default_generate_kwargs={
                "reasoning_effort": "max",
                "extra_body": {"thinking": {"type": "enabled"}},
            },
        )

        agent_dir = Path(__file__).resolve().parent
        code_dir = agent_dir.parent.parent.parent

        skill_hub = SkillHub(
            roots=[
                agent_dir / "skills",
                code_dir / "library" / "examples" / "simple_chat_agent" / "skills",
            ]
        )
        skill_registry = SkillRegistry(skill_hub, names=_BASE_SKILL_NAMES)

        tool_hub = ToolHub()
        tool_hub.register(make_read_file_tool(ALLOWED_ROOT))
        tool_hub.register(make_write_tool(ALLOWED_ROOT))
        tool_hub.register(make_search_replace_tool(ALLOWED_ROOT))
        tool_hub.register(make_list_pattern_tool(ALLOWED_ROOT))
        tool_hub.register(make_get_time_tool())
        tool_hub.register(make_append_log_tool(ALLOWED_ROOT))
        tool_hub.register(make_research_tool(ALLOWED_ROOT, tool_hub))
        tool_hub.register(make_load_skill_tool(skill_hub))
        tool_registry = ToolRegistry(tool_hub, names=_BASE_TOOL_NAMES)

        command_hub = CommandHub()
        for definition in _COMMANDS.values():
            command_hub.register(definition)
        command_registry = CommandRegistry(command_hub, names=list(_COMMANDS.keys()))

        return AgentComponents(
            model=model,
            tool_hub=tool_hub,
            tool_registry=tool_registry,
            skill_hub=skill_hub,
            skill_registry=skill_registry,
            command_hub=command_hub,
            command_registry=command_registry,
        )

    def build_system_prompt(self) -> str:
        return build_system_prompt(
            self.tool_registry,
            self.skill_registry,
            self.command_registry,
        )

    def _setup_turn(
        self,
        content: str,
        checkpoint_sha: str,
        command_match,
    ) -> None:
        """为本轮对话创建 context 和 loop——每次调用都是全新实例，不依赖 __init__ 中的旧值。"""
        system_prompt = self.build_system_prompt()
        if self.topic_id is not None:
            self.context = TopicContextManager(self.topic_id)
            self.context.begin_turn(
                content,
                checkpoint_sha,
                system_prompt,
                self.skill_hub,
                self.tool_hub,
                command_match,
            )
        else:
            self.context = TopicContextManager.ephemeral(
                history=[],
                user_text=content,
                system_prompt=system_prompt,
                skill_hub=self.skill_hub,
                tool_hub=self.tool_hub,
                command_match=command_match,
            )
        self.loop = ToolCallLoop(self.model, self.tool_hub, self.context)

    async def run(self, content: str) -> AsyncGenerator[str, None]:
        # ── 1. 命令解析 & 快照 ──
        command_match = parse_command_match(content, self.command_registry)
        checkpoint_sha = create_checkpoint()

        # ── 2. 上下文准备 ──
        self._setup_turn(content, checkpoint_sha, command_match)

        # ── 3. 工具合并（基础 + 命令触发）──
        tools = resolve_tools(
            self.tool_registry,
            self.tool_hub,
            command_match,
            self.command_registry,
        )
        loop_result: LoopResult | None = None

        try:
            # ── 4. LLM 流式循环 ──
            async for item in stream_loop_events(self.loop.run(tools=tools)):
                if isinstance(item, LoopResult):
                    loop_result = item
                    continue
                yield item

            if loop_result is None:
                loop_result = LoopResult()

            # ── 5. 后处理：文件变更 & 模式分数 ──
            modified_files = collect_modified_files(checkpoint_sha)
            append_action_messages(
                loop_result.new_messages,
                modified_files,
                loop_result.pattern_events,
            )

            # ── 6. 持久化 ──
            self.context.commit_turn(loop_result.new_messages)

            # ── 7. 最终事件 ──
            yield sse(
                "done",
                {
                    "new_messages": [m.model_dump() for m in loop_result.new_messages],
                    "modified_files": [m.model_dump() for m in modified_files],
                },
            )
        except Exception as exc:
            yield sse("error", {"message": str(exc)})


__all__ = ["ChatAgent", "build_system_prompt"]
