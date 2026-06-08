"""match_agent: 组装 model + tool + loop，评估模式与情境匹配度。"""

from code.config import api_key
from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry
from code.backend.models.schemas import PatternItem

from .prompt import _MATCH_PROMPT
from .submit_match_scores_tool import make_submit_tool
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


def match_patterns(
    situation: str,
    patterns: list[PatternItem],
    batch_size: int = 5,
) -> dict[str, float]:
    """评估一批模式与情境的匹配度，返回 {模式名: 匹配分}。"""
    scores: dict[str, float] = {}

    for i in range(0, len(patterns), batch_size):
        batch = patterns[i: i + batch_size]
        patterns_block = "\n".join(f"- {p.name}: {p.rel_path}" for p in batch)

        submit_tool = make_submit_tool()
        registry = ToolRegistry()
        registry.register(submit_tool)

        prompt = _MATCH_PROMPT.format(
            tools_block=_tools_text(registry),
            situation=situation,
            patterns_block=patterns_block,
        )

        model = _make_model()
        args = run_loop(model, registry, prompt, "请按照指示完成任务。", "submit_match_scores")
        if args:
            for item in args.get("scores", []):
                if isinstance(item, dict) and "name" in item:
                    try:
                        scores[item["name"]] = float(item.get("score", 0))
                    except (ValueError, TypeError):
                        scores[item["name"]] = 0.0

    return scores
