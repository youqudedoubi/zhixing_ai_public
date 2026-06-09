"""构建发送给 LLM 的完整消息列表。

这是"模型看到了什么"的唯一入口。
"""

import json
from pathlib import Path

from code.backend.models.schemas import Message
from code.backend.services.chat_agent.command.registry import CommandMatch, CommandRegistry
from code.backend.services.chat_agent.prompt.system_prompt import SYSTEM_PROMPT_TEMPLATE
from code.config import root
from code.library.agent_atoms.skills.skills_loader import SkillHub, SkillRegistry
from code.library.agent_atoms.tools.tools_loader import ToolHub, ToolRegistry

# ──────────────────────── 权限边界 ────────────────────────

ALLOWED_ROOT = Path(root).resolve()


# ──────────────────────── system prompt 组装 ────────────────────────


def _build_tools_text(
    tool_registry: ToolRegistry,
    command_registry: CommandRegistry,
) -> str:
    """从 ToolRegistry 生成工具列表文本，过滤掉命令专属工具。"""
    command_tools = command_registry.all_tool_names()
    lines = []
    for schema in tool_registry.get_tool_schemas():
        func = schema.get("function", {})
        name = func.get("name", "")
        if name in command_tools:
            continue
        lines.append(f"- {name}: {func.get('description', '')}")
    return "\n".join(lines) if lines else "（无）"


def _build_skills_text(
    skill_registry: SkillRegistry,
    command_registry: CommandRegistry,
) -> str:
    """从 SkillRegistry 生成 skill 列表文本，过滤掉命令专属 skill。"""
    command_skills = command_registry.all_skill_names()
    descriptions = skill_registry.get_descriptions()
    lines = [
        f"- {name}: {desc}"
        for name, desc in descriptions.items()
        if name not in command_skills
    ]
    return "\n".join(lines) if lines else "（无）"


def build_system_prompt(
    tool_registry: ToolRegistry,
    skill_registry: SkillRegistry,
    command_registry: CommandRegistry,
) -> str:
    """构建 system prompt：模板 + 动态工具/skill 列表。"""
    return SYSTEM_PROMPT_TEMPLATE.format(
        root_path=ALLOWED_ROOT,
        tools=_build_tools_text(tool_registry, command_registry),
        skills=_build_skills_text(skill_registry, command_registry),
    )


# ──────────────────────── 命令附加资源（内部）────────────────────────


def _command_already_used(
    command: str,
    history_messages: list[Message] | None,
) -> bool:
    """本轮之前用户已经用过同一条命令 → 不再重复附加资源。"""
    if not history_messages:
        return False
    return any(
        msg.role == "user" and msg.content.split()[0] == command
        for msg in history_messages
    )


def _build_attachment_parts(
    match: CommandMatch,
    skill_hub: SkillHub,
    tool_hub: ToolHub,
) -> list[str]:
    """将命令触发的 skill 描述和 tool schema 渲染为文本块。"""
    parts: list[str] = []
    if match.skill_names:
        descriptions = skill_hub.get_descriptions()
        for name in match.skill_names:
            parts.append(
                f"skill_name: {name}\n"
                f"skill_description: {descriptions.get(name, '')}"
            )
    if match.tool_names:
        for name in match.tool_names:
            func = tool_hub.get_schema_function(name)
            if not func:
                continue
            parts.append(
                f"tool_name: {name}\n"
                f"tool_description: {func.get('description', '')}\n"
                f"tool_parameters:\n{json.dumps(func.get('parameters', {}), ensure_ascii=False, indent=2)}"
            )
    return parts


# ──────────────────────── 用户消息组装 ────────────────────────


def build_user_message(
    user_text: str,
    match: CommandMatch | None,
    skill_hub: SkillHub,
    tool_hub: ToolHub,
    history_messages: list[Message] | None = None,
) -> str:
    """构建用户消息文本：在原始输入外包装 <user_query>，必要时附加命令资源。

    如果用户输入了 /命令 且本轮之前未使用过，则在消息末尾附加
    <manually_attached_message> 块，包含命令触发的 skill 描述和 tool schema。
    """
    assembled = f"<user_query>\n{user_text}"
    if match is None or _command_already_used(match.command, history_messages):
        return assembled

    parts = _build_attachment_parts(match, skill_hub, tool_hub)
    if not parts:
        return assembled
    return assembled + "\n<manually_attached_message>\n" + "\n\n".join(parts)


# ──────────────────────── 工具解析 ────────────────────────


def resolve_tools(
    tool_registry: ToolRegistry,
    tool_hub: ToolHub,
    match: CommandMatch | None,
    command_registry: CommandRegistry,
) -> list[dict]:
    """返回本轮可用工具 schema 列表：基础工具 + 命令触发的额外工具（去重）。"""
    available = tool_registry.get_tool_schemas()
    if match is None:
        return available

    existing = {
        schema.get("function", {}).get("name")
        for schema in available
    }
    for name in match.tool_names:
        if name in existing:
            continue
        func = tool_hub.get_schema_function(name)
        if func:
            available.append({"type": "function", "function": func})
    return available


# ──────────────────────── 历史消息规范化 ────────────────────────


def convert_history_to_messages(messages: list[Message]) -> list[dict]:
    """将应用的 Message 对象列表转换为 LLM API 期望的 dict 格式。

    处理 assistant 消息中的 tool_calls 以及对应的 tool 角色消息。
    """
    result: list[dict] = []
    for msg in messages:
        if msg.role == "user":
            result.append({"role": "user", "content": msg.content})
            continue
        if msg.role == "assistant":
            entry: dict = {"role": "assistant", "content": msg.content}
            if msg.reasoning_content:
                entry["reasoning_content"] = msg.reasoning_content
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.call_id or f"{tc.tool_name}_{i}",
                        "type": "function",
                        "function": {
                            "name": tc.tool_name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for i, tc in enumerate(msg.tool_calls)
                ]
            result.append(entry)
            if msg.tool_calls:
                for i, tc in enumerate(msg.tool_calls):
                    if tc.result:
                        result.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.call_id or f"{tc.tool_name}_{i}",
                                "content": tc.result,
                            }
                        )
    return result


# ──────────────────────── 完整消息列表 ────────────────────────


def build_messages(
    system_prompt: str,
    history: list[Message],
    user_text: str,
    skill_hub: SkillHub,
    tool_hub: ToolHub,
    command_match: CommandMatch | None,
) -> list[dict]:
    """组装完整的消息列表：system prompt → 历史消息 → 当前用户消息。"""
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    messages.extend(convert_history_to_messages(history))
    messages.append(
        {
            "role": "user",
            "content": build_user_message(
                user_text,
                command_match,
                skill_hub,
                tool_hub,
                history,
            ),
        }
    )
    return messages
