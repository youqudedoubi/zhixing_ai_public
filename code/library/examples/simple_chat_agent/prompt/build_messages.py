"""构建发送给 LLM 的完整消息列表。

这是"模型看到了什么"的唯一入口。
"""

from pathlib import Path

from code.library.agent_atoms.skills.skills_loader import SkillRegistry
from code.library.agent_atoms.tools.registry import ToolRegistry
from code.library.examples.simple_chat_agent.prompt.system_prompt import SYSTEM_PROMPT_TEMPLATE


# ──────────────────────── system prompt 组装 ────────────────────────


def _build_tools_text(tool_registry: ToolRegistry) -> str:
    """从 ToolRegistry 生成工具列表文本（用于嵌入 system prompt）。"""
    lines = []
    for schema in tool_registry.get_tool_schemas():
        func = schema.get("function", {})
        name = func.get("name", "")
        lines.append(f"- {name}: {func.get('description', '')}")
    return "\n".join(lines) if lines else "（无）"


def _build_skills_text(skill_registry: SkillRegistry) -> str:
    """从 SkillRegistry 生成 skill 列表文本（用于嵌入 system prompt）。"""
    descriptions = skill_registry.get_descriptions()
    lines = [f"- {name}: {desc}" for name, desc in descriptions.items()]
    return "\n".join(lines) if lines else "（无）"


def build_system_prompt(
    tool_registry: ToolRegistry,
    skill_registry: SkillRegistry,
    root_path: Path | None = None,
) -> str:
    """构建 system prompt：模板 + 动态工具/skill 列表。"""
    return SYSTEM_PROMPT_TEMPLATE.format(
        root_path=root_path or Path.cwd(),
        tools=_build_tools_text(tool_registry),
        skills=_build_skills_text(skill_registry),
    )


# ──────────────────────── 用户消息组装 ────────────────────────


def build_user_message(user_text: str) -> str:
    """构建用户消息文本：用 <user_query> 包裹原始输入。"""
    return f"<user_query>\n{user_text}"


# ──────────────────────── 历史消息规范化 ────────────────────────


def convert_history_to_messages(history: list[dict]) -> list[dict]:
    """将历史 dict 消息转换为 LLM API 期望的格式。

    历史消息以 dict 格式存储，此函数做一次规范化的遍历：
    - 按 role 分类，确保字段名符合 LLM API 约定
    - assistant 消息中的 tool_calls 原样保留
    - tool 消息保留 tool_call_id
    """
    result: list[dict] = []
    for msg in history:
        role = msg.get("role", "")
        if role == "system":
            result.append({"role": "system", "content": msg.get("content", "")})
        elif role == "user":
            result.append({"role": "user", "content": msg.get("content", "")})
        elif role == "assistant":
            entry: dict = {
                "role": "assistant",
                "content": msg.get("content") or "",
            }
            if msg.get("tool_calls"):
                entry["tool_calls"] = msg["tool_calls"]
            result.append(entry)
        elif role == "tool":
            result.append(
                {
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "content": msg.get("content", ""),
                }
            )
        else:
            result.append(msg)
    return result


# ──────────────────────── 完整消息列表 ────────────────────────


def build_messages(
    system_prompt: str,
    history: list[dict],
    user_text: str,
) -> list[dict]:
    """组装完整的消息列表：system prompt → 历史消息 → 当前用户消息。"""
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    messages.extend(convert_history_to_messages(history))
    messages.append(
        {
            "role": "user",
            "content": build_user_message(user_text),
        }
    )
    return messages
