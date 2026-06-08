"""flow_agent: 组装 model + tools + loop，将模式卡片转换为思维流。

对外接口：generate_flows() — 并发处理一批模式文件，写入思维流。
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from code.config import api_key
from code.library.agent_atoms.llm.BaseModel import BaseModel
from code.library.agent_atoms.tools.registry import ToolRegistry

from .prompt import _FLOW_PROMPT
from .submit_thought_flow_tool import make_submit_tool
from .read_diary_tool import make_read_diary_tool
from .tool_call_loop import run_loop

# ── Model kwargs ──────────────────────────────────────────────────────────────
_MODEL_KWARGS = {
    "model_name": "deepseek-v4-pro",
    "base_url": "https://api.deepseek.com",
}


def _make_model() -> BaseModel:
    return BaseModel(api_key=api_key, **_MODEL_KWARGS)


def _extract_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_block, body). frontmatter_block includes --- delimiters."""
    m = re.match(r"^(---\s*\n.*?\n---)\s*\n?", text, re.DOTALL)
    if m:
        return m.group(1), text[m.end():]
    return "", text


def _tools_text(registry: ToolRegistry) -> str:
    return "\n".join(
        f"- {s['function']['name']}: {s['function']['description']}"
        for s in registry.get_tool_schemas()
    )


def _pattern_to_flow_agent(pattern_path: Path, root: Path) -> str:
    """为单个模式卡片生成思维流。返回思维流正文（不含 frontmatter）。"""
    pattern_text = pattern_path.read_text(encoding="utf-8")

    result_holder: dict = {}

    registry = ToolRegistry()
    registry.register(make_read_diary_tool(root))
    registry.register(make_submit_tool(result_holder))

    system_prompt = _FLOW_PROMPT.format(
        tools=_tools_text(registry),
        pattern=pattern_text,
    )

    model = _make_model()
    content = run_loop(
        model=model,
        registry=registry,
        system_prompt=system_prompt,
        user_message="请根据以上模式卡片生成思维流。",
        target_tool="submit_thought_flow",
        result_holder=result_holder,
    )
    return content or ""


def _write_flow_to_file(pattern_path: Path, flow_body: str) -> None:
    """将思维流正文写回文件，保留原有 frontmatter。"""
    original = pattern_path.read_text(encoding="utf-8")
    frontmatter, _ = _extract_frontmatter(original)
    if frontmatter:
        new_text = frontmatter + "\n" + flow_body.strip() + "\n"
    else:
        new_text = flow_body.strip() + "\n"
    pattern_path.write_text(new_text, encoding="utf-8")


def generate_flows(
    pattern_paths: list[Path],
    root: Path,
    emit: Callable[[str], None],
    max_workers: int = 8,
) -> None:
    """并发为所有模式文件生成思维流。"""
    total = len(pattern_paths)
    if total == 0:
        return

    completed = 0

    def _process(path: Path) -> tuple[Path, str]:
        return path, _pattern_to_flow_agent(path, root)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process, p): p for p in pattern_paths}
        for future in as_completed(futures):
            path = futures[future]
            name = path.stem
            try:
                _, flow_body = future.result()
                if flow_body:
                    _write_flow_to_file(path, flow_body)
                else:
                    emit(f"data: {json.dumps({'type': 'flow_warning', 'pattern_name': name, 'message': '空的思维流'}, ensure_ascii=False)}\n\n")
            except Exception as e:
                emit(f"data: {json.dumps({'type': 'flow_error', 'pattern_name': name, 'error': str(e)}, ensure_ascii=False)}\n\n")
            finally:
                completed += 1
                emit(f"data: {json.dumps({'type': 'flow_done', 'pattern_name': name, 'current': completed, 'total': total}, ensure_ascii=False)}\n\n")
