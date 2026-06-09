"""Research Agent Team：组装 mentor → analyze ↔ critic 三人团队。

架构：
- 每个 Agent 自包含一个文件夹，结构参考 library/examples/simple_chat_agent。
- 下级 Agent 是上级 Agent 的工具：send_message 是纯消息传递，loop 检测到后做分派。
- 两个 loop 类型：supervisor_loop（调度下级→继续），worker_loop（向上汇报→退出/调度 peer→继续）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from code.shared.data_paths import RESEARCH_DIR
from code.backend.services.research.mentor_agent import MentorAgent
from code.backend.services.research.analyze_agent import AnalyzeAgent
from code.backend.services.research.critic_agent import CriticAgent

EmitFn = Callable[[str, str, str], None]  # (agent_name, content, msg_type)


def _safe_topic(topic: str) -> str:
    """将课题名称转为安全的目录名片段。"""
    return topic.strip().replace("/", "_").replace("\\", "_")[:60]


def run_research(
    topic: str,
    allowed_root: Path,
    pattern_text: str,
    emit: EmitFn,
) -> tuple[str, list[dict]]:
    """运行完整的研究流水线。返回 (report_path_str, process_log)。"""
    # ── 路径 ──
    research_dir = allowed_root / RESEARCH_DIR / _safe_topic(topic)
    research_dir.mkdir(parents=True, exist_ok=True)
    report_path = research_dir / "research_report.md"

    # ── 共享状态 ──
    process_log: list[dict] = []

    # ── 组装 Agent 依赖链（下级注入给上级） ──
    critic = CriticAgent(
        allowed_root=allowed_root,
        pattern_text=pattern_text,
        emit=emit,
        process_log=process_log,
    )
    analyze = AnalyzeAgent(
        allowed_root=allowed_root,
        pattern_text=pattern_text,
        emit=emit,
        process_log=process_log,
        critic=critic,
    )
    mentor = MentorAgent(
        allowed_root=allowed_root,
        pattern_text=pattern_text,
        report_path=report_path,
        emit=emit,
        process_log=process_log,
        analyze=analyze,
    )

    # ── 启动 mentor，由它驱动整个研究流程 ──
    mentor.run(topic)

    # ── 保存 process_log ──
    process_json = research_dir / "research_process.json"
    process_json.write_text(
        json.dumps(process_log, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return str(report_path), process_log
