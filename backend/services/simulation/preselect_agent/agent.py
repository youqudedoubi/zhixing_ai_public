"""preselect_agent: 组装 model + tool + loop，从全部模式中预选候选。"""

from code.config import api_key
from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry
from code.backend.models.schemas import PatternItem

from .prompt import _PRESELECT_PROMPT
from .submit_preselected_patterns_tool import make_submit_tool
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


def preselect_patterns(situation: str, patterns: list[PatternItem]) -> list[str]:
    """从全部模式中预选出与情境相关的候选，返回选中模式名列表。"""
    overview = "\n".join(f"- {p.name}: {p.rel_path}" for p in patterns)

    submit_tool = make_submit_tool()
    registry = ToolRegistry()
    registry.register(submit_tool)

    prompt = _PRESELECT_PROMPT.format(
        tools=_tools_text(registry),
        situation=situation,
        patterns_overview=overview,
    )

    model = _make_model()
    args = run_loop(model, registry, prompt, "请按照指示完成任务。", "submit_preselected_patterns")
    selected = args.get("patterns", []) if args else []
    return [p["name"] for p in selected if isinstance(p, dict) and "name" in p]
