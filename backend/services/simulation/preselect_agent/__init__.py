"""preselect_agent: 从全部 CBT 模式中预选出与当前情境相关的候选模式。

宁可多选，不要漏掉有合理可能的模式。
"""

from .agent import preselect_patterns

__all__ = ["preselect_patterns"]
