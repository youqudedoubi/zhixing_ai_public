"""模拟引擎：编排管线 → 预选 → 匹配 → DFS 模拟。

三个 Agent（各自独立文件夹）：
  preselect_agent  – 从全部模式中预选候选
  match_agent      – 评估候选模式的情境匹配度
  simulate_agent   – 生成 DFS 单个节点的思维内容

引擎本身负责：
  - 输入验证、管线编排
  - 优先级计算（匹配分 + 强度混合）
  - 思维流文件解析
  - DFS 推进 + 随机触发 + 结果树组装
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from code.backend.models.schemas import SimulationNode, SimulationResult, PatternItem
from code.backend.services.simulation import SIM_DIR, CONFIG_DIR, _PHASE_NAMES
from code.backend.services.simulation.preselect_agent import preselect_patterns
from code.backend.services.simulation.match_agent import match_patterns
from code.backend.services.simulation.simulate_agent import simulate_node

# ── Tunables ────────────────────────────────────────────────────────────────────

# MATCH_THRESHOLD：情境匹配分数（0-1）低于此值的模式将被丢弃，不进入优先级排名。
#   在 v1.2 样本上手动调优；设置为 <0.1 会导致不相关的模式大量通过过滤。
MATCH_THRESHOLD = 0.2

# FALLBACK_MATCH：当所有候选都低于阈值时使用的默认匹配分数。
#   防止所有模式都没有明确匹配时产生空结果。
FALLBACK_MATCH = 0.3


# ── Phase state helpers ─────────────────────────────────────────────────────────

def _parse_flow_sections(flow_content: str) -> dict[str, str]:
    """解析思维流 markdown 为 {阶段名: 内容} 字典。

    预期格式（兼容 ## 和 ### 标题）：
        ## 第一反应
        <内容>
        ## 次生思维
        <内容>
        ...

    阶段缺失时返回空字符串。
    """
    result: dict[str, str] = {}
    for phase in _PHASE_NAMES:
        m = re.search(
            rf"(?:^|\n)#{{2,3}}\s*{re.escape(phase)}\s*\n(.*?)(?=\n#{{2,3}}\s|\Z)",
            flow_content, re.DOTALL,
        )
        result[phase] = m.group(1).strip() if m else ""
    return result


def _get_phases_from_flow(flow_content: str) -> list[str]:
    """返回思维流文件中存在的非空阶段列表（至少返回第一个阶段）。"""
    sections = _parse_flow_sections(flow_content)
    phases = [p for p in _PHASE_NAMES if sections[p] and sections[p] != "空"]
    return phases if phases else [_PHASE_NAMES[0]]


def _get_phase_content(flow_content: str, phase: str) -> str:
    """返回思维流中指定阶段的内容文本。"""
    return _parse_flow_sections(flow_content).get(phase, "")


# ── Priority helper ────────────────────────────────────────────────────────────

def _compute_priority(match_score: float, intensity: float, alpha: float) -> float:
    """将情境匹配度（0-1）与模式固有强度（0-100）按 alpha 混合为优先级。

    alpha=1.0 → 仅看匹配 | alpha=0.0 → 仅看强度 | 默认 0.6 → 偏向匹配
    """
    return alpha * match_score + (1 - alpha) * (intensity / 100.0)


# ── Main simulation ─────────────────────────────────────────────────────────────

@dataclass
class SimulationConfig:
    """不可变的模拟配置与预处理结果。

    将 DFS 需要的所有只读数据集中在一起，可变累积器（all_nodes）单独管理。
    """
    situation: str
    config_name: str
    root: Path
    max_branches: int
    max_steps: int
    alpha: float
    candidates: list[tuple[PatternItem, float]]  # (模式, 优先级)，按优先级降序
    flow_map: dict[str, str]                      # 模式名 → 思维流 markdown


def _load_flow_content(root: Path, config_name: str, rel_path: str) -> str:
    """读取思维流文件内容。"""
    path = root / SIM_DIR / CONFIG_DIR / config_name / rel_path
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _select_and_rank_triggers(
    candidates: list[tuple[PatternItem, float]],
    phase_map: dict[str, list[str]],
    max_branches: int,
    rng: random.Random,
) -> list[PatternItem]:
    """随机筛选 + 优先级排序 + 截断。返回本层触发的模式列表。"""
    triggered: list[tuple[PatternItem, float]] = []
    for p, priority in candidates:
        if p.name not in phase_map or not phase_map[p.name]:
            continue
        if rng.random() < priority:
            triggered.append((p, priority))

    if not triggered:
        return []

    triggered.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in triggered[:max_branches]]


def _execute_single_node(
    config: SimulationConfig,
    all_nodes: dict[str, SimulationNode],
    emit: Callable[[str], None],
    _sse: Callable[[str, dict], str],
    pattern: PatternItem,
    phase: str,
    node_path_id: str,
    parent: SimulationNode,
    history: str,
) -> SimulationNode:
    """执行单个模拟节点：SSE 通知 → LLM 生成 → 创建节点 → SSE 通知。"""
    emit(_sse("node_start", {
        "node_id": node_path_id,
        "pattern_name": pattern.name,
        "phase": phase,
        "parent_id": parent.id,
    }))

    content = simulate_node(
        situation=config.situation,
        history=history,
        flow_content=config.flow_map[pattern.name],
        phase=phase,
    )

    node = SimulationNode(
        id=node_path_id,
        pattern_name=pattern.name,
        phase=phase,
        content=content,
        parent_id=parent.id,
    )
    all_nodes[node_path_id] = node
    parent.children.append(node)

    emit(_sse("node_done", {"node_id": node_path_id, "content": content}))
    return node


def _dfs_step(
    config: SimulationConfig,
    all_nodes: dict[str, SimulationNode],
    emit: Callable[[str], None],
    step: int,
    history: str,
    phase_map: dict[str, list[str]],
    parent: SimulationNode,
    parent_path_id: str,
    _sse: Callable[[str, dict], str],
    rng: random.Random,
) -> None:
    """DFS 遍历的单步：筛选触发模式 → 逐个执行节点 → 递归下一阶段。"""
    if step > config.max_steps:
        return

    selected = _select_and_rank_triggers(config.candidates, phase_map, config.max_branches, rng)

    for branch_idx, pattern in enumerate(selected):
        phases = phase_map[pattern.name]
        if not phases:
            continue
        current_phase = phases[0]

        # 点分路径 ID: "1" → "1.1", "1.2"; "1.2" → "1.2.1", "1.2.2"
        node_path_id = f"{parent_path_id}.{branch_idx + 1}"

        node = _execute_single_node(
            config, all_nodes, emit, _sse,
            pattern, current_phase, node_path_id, parent, history,
        )

        # 为递归更新阶段映射（深拷贝以避免干扰兄弟分支）
        new_phase_map = {k: list(v) for k, v in phase_map.items()}
        remaining = phases[1:]
        if remaining:
            new_phase_map[pattern.name] = remaining
        else:
            del new_phase_map[pattern.name]

        new_history = history + f"\n[{pattern.name} - {current_phase}] {node.content}"
        _dfs_step(config, all_nodes, emit, step + 1, new_history, new_phase_map, node, node_path_id, _sse, rng)


def run_simulation(
    situation: str,
    config_name: str,
    patterns: list[PatternItem],
    root: Path,
    max_branches: int,
    max_steps: int,
    alpha: float,
    emit: Callable[[str], None],
    seed: int | None = None,
) -> SimulationResult:
    """运行完整模拟管线。emit 推送 SSE 字符串。

    管线步骤:
      1. 输入验证
      2. 预选 — preselect_agent 从所有模式中选择与情境相关的模式
      3. 匹配评分 — match_agent 给每个预选模式打出 0-1 的匹配分
      4. 优先级计算 — 将匹配分与模式固有强度按 alpha 混合
      5. DFS 模拟 — simulate_agent 递归推进各阶段的思维流节点

    seed 用于控制 DFS 中的随机触发（可复现结果），None 时使用系统熵源。
    """
    # ── 输入验证 ──
    if max_branches < 1:
        raise ValueError(f"max_branches 必须 >= 1，实际为 {max_branches}")
    if max_steps < 1:
        raise ValueError(f"max_steps 必须 >= 1，实际为 {max_steps}")
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha 必须在 [0, 1] 之间，实际为 {alpha}")
    if not situation.strip():
        raise ValueError("situation 不能为空")

    def _sse(event_type: str, data: dict) -> str:
        payload = {"type": event_type, **data}
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    # ── 步骤 1: 预选 ──
    emit(_sse("sim_status", {"message": "正在预选模式..."}))
    selected_names = preselect_patterns(situation, patterns)
    if not selected_names:
        selected_names = [p.name for p in patterns]

    candidate1 = [p for p in patterns if p.name in selected_names]

    # ── 步骤 2: 匹配评分 ──
    emit(_sse("sim_status", {"message": f"正在评估 {len(candidate1)} 个模式的情境匹配度..."}))
    match_scores = match_patterns(situation, candidate1)

    # ── 步骤 3: 计算优先级并按阈值筛选 ──
    candidates: list[tuple[PatternItem, float]] = []
    for p in candidate1:
        match = match_scores.get(p.name, 0.0)
        if match < MATCH_THRESHOLD:
            continue
        candidates.append((p, _compute_priority(match, p.intensity, alpha)))

    # 后备：若没有模式达到阈值，对所有候选使用默认匹配分
    if not candidates:
        candidates = [
            (p, _compute_priority(match_scores.get(p.name, FALLBACK_MATCH), p.intensity, alpha))
            for p in candidate1
        ]

    # ── 加载思维流 & 构建阶段映射 ──
    flow_map: dict[str, str] = {}
    phase_state_map: dict[str, list[str]] = {}
    for p, _ in candidates:
        flow_map[p.name] = _load_flow_content(root, config_name, p.rel_path)
        phase_state_map[p.name] = _get_phases_from_flow(flow_map[p.name])

    # ── 构建结果树根节点 ──
    result_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    root_node = SimulationNode(
        id="1",
        pattern_name="",
        phase="",
        content=situation,
        parent_id=None,
    )
    all_nodes: dict[str, SimulationNode] = {"1": root_node}

    config = SimulationConfig(
        situation=situation,
        config_name=config_name,
        root=root,
        max_branches=max_branches,
        max_steps=max_steps,
        alpha=alpha,
        candidates=candidates,
        flow_map=flow_map,
    )

    rng = random.Random(seed)

    emit(_sse("simulation_start", {"max_branches": max_branches, "max_steps": max_steps}))
    emit(_sse("sim_status", {"message": "开始模拟..."}))

    # ── 步骤 4: DFS 模拟 ──
    _dfs_step(config, all_nodes, emit, 1, "", phase_state_map, root_node, "1", _sse, rng)

    # ── 组装结果 ──
    result = SimulationResult(
        id=result_id,
        name=f"模拟 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        config_name=config_name,
        situation=situation,
        max_branches=max_branches,
        max_steps=max_steps,
        alpha=alpha,
        created_at=datetime.now().isoformat(),
        root=root_node,
    )

    emit(_sse("simulation_done", {"result_id": result_id}))
    return result
