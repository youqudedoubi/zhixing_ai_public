"""构建 analyze_agent 的系统提示。"""
from __future__ import annotations

from code.library.agent_atoms.tools.registry import ToolRegistry
from code.backend.services.research.analyze_agent.prompt.prompt import ANALYZE_SYSTEM


def _build_tools_text(registry: ToolRegistry) -> str:
    lines = []
    for schema in registry.get_tool_schemas():
        f = schema.get("function", {})
        name = f.get("name", "")
        desc = f.get("description", "")
        params = f.get("parameters", {}).get("properties", {})
        if params:
            lines.append(f"- {name}({', '.join(params.keys())}): {desc}")
        else:
            lines.append(f"- {name}: {desc}")
    return "\n".join(lines)


def build_system_prompt(registry: ToolRegistry, pattern_text: str) -> str:
    return ANALYZE_SYSTEM.format(
        pattern=pattern_text,
        tools_block=_build_tools_text(registry),
    )
