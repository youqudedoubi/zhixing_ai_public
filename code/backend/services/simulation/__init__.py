"""模拟管道：CBT 模式卡片 → 思维流 → DFS 模拟。

数据流：
  1. config_service    — 管理 simulation_config/ 目录，列出/复制/修改模式
  2. flow_agent        — 为每个模式卡片运行 LLM（通过 ThreadPoolExecutor 并发），
                         生成"思维流"（分阶段的反应文本）
  3. simulation_engine — 主模拟：预选匹配模式，通过匹配分数+优先级 DFS 推进各阶段，
                         返回 SimulationResult 树
  4. result_service    — 将 SimulationSession 和 SimulationResult JSON 持久化到磁盘

Agent 目录结构（library 风格，每个 agent 独立文件夹）：
  flow_agent/       — 模式→思维流
  preselect_agent/  — 预选候选模式
  match_agent/      — 情境匹配评分
  simulate_agent/   — 单节点内容生成

修改指南：
  - 调整 LLM 提示词 → 对应 agent 的 prompt.py
  - 更改场景       → zhixing_data/simulation/simulation_config/<name>/ 下的模式文件
  - 更改匹配/优先级逻辑 → simulation_engine.py 中的 run_simulation()
  - 添加/删除阶段  → 下面的 PHASES 列表
  - 文件系统布局   → 下面的路径常量
"""

from __future__ import annotations

# ── 路径常量 ────────────────────────────────────────────────────────────────
SIM_DIR = "simulation"
CONFIG_DIR = "simulation_config"
RESULT_DIR = "simulation_result"
PATTERN_CATEGORIES = ("positive", "negative", "neutral")
DEFAULT_CONFIG_NAME = "default_mode"
SESSIONS_FILE = "simulation_sessions.json"

# ── 阶段定义（CBT 思维流的三个阶段，集中管理） ──────────────────────────────
PHASES: list[dict[str, str]] = [
    {"name": "第一反应", "description": "下意识的、自动的反应"},
    {"name": "次生思维", "description": "由第一反应激发、衍生的思维"},
    {"name": "强化思维", "description": "更多的、进一步的想法"},
]
_PHASE_NAMES = [p["name"] for p in PHASES]
