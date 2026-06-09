"""match_agent: 评估一批 CBT 模式与当前情境的匹配程度（0-1 分数）。"""

from .agent import match_patterns

__all__ = ["match_patterns"]
