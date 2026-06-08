"""研究模块：多 Agent 协作分析日记与模式，生成洞察报告。

架构（每个 Agent 自包含一个文件夹）：
    mentor_agent/    — supervisor_loop，调度 analyze
    analyze_agent/   — worker_loop，研究 + 调度 critic
    critic_agent/    — worker_loop，质疑 + 回复 analyze
    agent_team.py    — 组装三者并启动流水线

公共 API：
    run_research()   — 运行完整研究流水线（同步）
"""
from code.backend.services.research.agent_team import run_research

__all__ = ["run_research"]
