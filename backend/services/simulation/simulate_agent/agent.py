"""simulate_agent: 组装 model + tool + loop，生成单个模拟节点的思维内容。

内部含重试：若 LLM 完全未调用提交工具，重试一次。
"""

from code.config import api_key
from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry

from .prompt import _SIMULATE_PROMPT
from .submit_simulation_result_tool import make_submit_tool
from .tool_call_loop import run_loop

# ── Model kwargs ──────────────────────────────────────────────────────────────
_MODEL_KWARGS = {
    "model_name": "deepseek-v4-pro",
    "base_url": "https://api.deepseek.com",
}


def _make_model() -> BaseModel:
    return BaseModel(api_key=api_key, **_MODEL_KWARGS)


def _tools_text(registry: ToolRegistry) -> str:
    return "\n".join(
        f"- {s['function']['name']}: {s['function']['description']}"
        for s in registry.get_tool_schemas()
    )


def simulate_node(
    situation: str,
    history: str,
    flow_content: str,
    phase: str,
) -> str:
    """为 DFS 模拟生成单个节点的思维内容。

    若 LLM 完全未调用提交工具（返回 None），重试一次；
    若工具被调用但内容为空，不重试（重试无意义）。
    """
    submit_tool = make_submit_tool()
    registry = ToolRegistry()
    registry.register(submit_tool)

    prompt = _SIMULATE_PROMPT.format(
        tools_block=_tools_text(registry),
        situation=situation,
        history=history or "（无前文）",
        flow_content=flow_content,
        phase=phase,
    )

    model = _make_model()
    args = run_loop(model, registry, prompt, "请按照指示完成任务。", "submit_simulation_result")
    content = args.get("content", "") if args else ""

    if args is None:
        model = _make_model()
        args = run_loop(model, registry, prompt, "请按照指示完成任务。", "submit_simulation_result")
        content = args.get("content", "") if args else ""

    return content
