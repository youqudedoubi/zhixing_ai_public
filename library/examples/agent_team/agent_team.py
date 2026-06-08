"""Agent Team 示例：组装 Boss → Worker 二人团队。

展示多 Agent 协作的核心模式：
  - 每个 Agent 自包含一个文件夹（tools / prompt / loop）
  - send_message 是纯消息传递工具（两个 Agent 各持一份完全相同的拷贝）
  - 路由在 loop 里：supervisor_loop 调度下级，worker_loop 向上汇报
  - agent_team.py 只做组装——创建 Agent 实例，注入依赖，启动运行
"""
import json
from typing import Callable

from code.library.examples.agent_team.boss_agent import BossAgent
from code.library.examples.agent_team.worker_agent import WorkerAgent

EmitFn = Callable[[str, str, str], None]  # (agent_name, content, msg_type)


def run_team(task: str, emit: EmitFn | None = None) -> tuple[str, list[dict]]:
    """运行 Boss + Worker 团队。返回 (最终回复, process_log)。"""
    if emit is None:
        def emit(agent_name: str, content: str, msg_type: str) -> None:
            pass

    process_log: list[dict] = []

    # ── 组装依赖链（下级注入给上级）──
    worker = WorkerAgent(emit=emit, process_log=process_log)
    boss = BossAgent(emit=emit, process_log=process_log, worker=worker)

    # ── 启动 boss，由它驱动整个流程 ──
    result = boss.run(task)

    return result, process_log


# ------------------------------------------------------------------
# 最小化演示（不需要实际 LLM 调用即可看到组装逻辑）
# ------------------------------------------------------------------

if __name__ == "__main__":
    print("Agent Team 示例结构：")
    print()
    worker = WorkerAgent(emit=lambda *a: None, process_log=[])
    boss = BossAgent(emit=lambda *a: None, process_log=[], worker=worker)

    print(f"  BossAgent 工具: {[t.get('function', {}).get('name') for t in boss.registry.get_tool_schemas()]}")
    print(f"  WorkerAgent 工具: {[t.get('function', {}).get('name') for t in worker.registry.get_tool_schemas()]}")
    print(f"  Boss loop: {type(boss.loop).__name__}")
    print(f"  Worker loop: {type(worker.loop).__name__}")
    print()
    print("  通信流程：用户 → Boss → send_message(to='worker_agent')")
    print("           Boss.loop 检测 send_message → worker.run(task)")
    print("           Worker 执行 → send_message(to='boss_agent')")
    print("           Worker.loop 检测 send_message → return 消息")
    print("           Boss.loop 收到回复 → 继续或结束")
