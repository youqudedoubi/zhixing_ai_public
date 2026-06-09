"""match_agent: 组装 model + tool + loop，评估模式与情境匹配度。

使用 Scheduler 并发处理多个批次，减少评估阶段的等待时间。
"""

from code.config import api_key
from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry
from code.library.infra.scheduler import Scheduler
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


def _match_one_batch(
    situation: str,
    batch: list[PatternItem],
) -> dict[str, float]:
    """对单个批次的模式评估匹配度，返回 {模式名: 匹配分}。"""
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

    scores: dict[str, float] = {}
    if args:
        for item in args.get("scores", []):
            if isinstance(item, dict) and "name" in item:
                try:
                    scores[item["name"]] = float(item.get("score", 0))
                except (ValueError, TypeError):
                    scores[item["name"]] = 0.0
    return scores


def match_patterns(
    situation: str,
    patterns: list[PatternItem],
    batch_size: int = 5,
    max_workers: int = 6,
) -> dict[str, float]:
    """评估一批模式与情境的匹配度，返回 {模式名: 匹配分}。

    内部将模式按 batch_size 切分为多个批次，通过 Scheduler 并发调用 LLM。
    """
    if not patterns:
        return {}

    batches = [patterns[i: i + batch_size] for i in range(0, len(patterns), batch_size)]

    scheduler = Scheduler(max_workers=max_workers)
    batch_results = scheduler.map_ordered(
        fn=lambda b: _match_one_batch(situation, b),
        items=batches,
        desc="评估情境匹配度",
        disable=True,
    )

    all_scores: dict[str, float] = {}
    for scores in batch_results:
        all_scores.update(scores)
    return all_scores
