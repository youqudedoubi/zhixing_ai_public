"""相对于用户数据根目录 (zhixing_data/) 的路径片段。

调用方用 allowed_root / 常量名 获得完整路径。
不在本模块中存绝对路径——它依赖运行时的 allowed_root。
"""
from pathlib import Path

PATTERN_DIR = Path("analysis") / "pattern"
DIARY_DIR = Path("raw") / "diary"
RESEARCH_DIR = Path("analysis") / "research"
