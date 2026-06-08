"""flow_agent: 将 CBT 模式卡片转换为"思维流"格式。

每个模式卡片（analysis/pattern/ 下的 pattern.md）经过 LLM 处理后，
生成包含"第一反应"→"次生思维"→"强化思维"的分阶段文本。
通过 ThreadPoolExecutor 并发处理（BaseModel 是同步的）。
"""

from .agent import generate_flows

__all__ = ["generate_flows"]
