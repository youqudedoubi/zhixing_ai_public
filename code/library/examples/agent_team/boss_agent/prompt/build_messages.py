"""构建 boss_agent 的系统提示。"""
from code.library.agent_atoms.tools.registry import ToolRegistry
from code.library.examples.agent_team.boss_agent.prompt.prompt import BOSS_SYSTEM


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


def build_system_prompt(registry: ToolRegistry) -> str:
    return BOSS_SYSTEM.format(tools=_build_tools_text(registry))
