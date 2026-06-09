"""Simulation config management: list configs, update default, create new, manage patterns."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Callable

from code.backend.models.schemas import PatternItem
from code.backend.services.simulation import SIM_DIR, CONFIG_DIR, PATTERN_CATEGORIES, DEFAULT_CONFIG_NAME
from code.backend.services.simulation.flow_agent import generate_flows

_ANALYSIS_PATTERN_SRC = "analysis/pattern"


def _sim_root(root: Path) -> Path:
    return root / SIM_DIR


def _config_dir(root: Path) -> Path:
    return _sim_root(root) / CONFIG_DIR


def _parse_frontmatter(text: str) -> dict:
    """从 markdown frontmatter 中提取 YAML 样式的键值对。

    仅处理简单的单行键值（不支持嵌套或引号）。
    按第一个 ':' 分割，因此值中可以包含冒号。
    """
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    result: dict = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        # 仅按第一个 ':' 分割——值中可以包含冒号
        if ":" in line:
            k, v = line.split(":", 1)
            result[k.strip()] = v.strip()
    return result


def _update_frontmatter_intensity(text: str, intensity: float) -> str:
    """Replace intensity value in frontmatter."""
    def replacer(m: re.Match) -> str:
        block = m.group(1)
        block = re.sub(r"(intensity\s*[:：]\s*)[\d.]+", rf"\g<1>{intensity}", block)
        return f"---\n{block}\n---"
    result = re.sub(r"^---\s*\n(.*?)\n---", replacer, text, flags=re.DOTALL)
    return result


def list_configs(root: Path) -> list[str]:
    """Return list of config directory names under simulation_config/."""
    cfg_dir = _config_dir(root)
    if not cfg_dir.exists():
        return []
    return sorted(
        d.name for d in cfg_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def list_patterns(root: Path, config_name: str) -> list[PatternItem]:
    """Return all .md pattern files in a config (excluding log.md)."""
    cfg = _config_dir(root) / config_name
    if not cfg.exists():
        return []
    items: list[PatternItem] = []
    for category in PATTERN_CATEGORIES:
        cat_dir = cfg / category
        if not cat_dir.exists():
            continue
        for f in sorted(cat_dir.glob("*.md")):
            if f.name == "log.md":
                continue
            text = f.read_text(encoding="utf-8")
            fm = _parse_frontmatter(text)
            name = fm.get("name", f.stem)
            try:
                intensity = float(fm.get("intensity", 50))
            except ValueError:
                intensity = 50.0
            rel = f"{category}/{f.name}"
            items.append(PatternItem(rel_path=rel, name=name, category=category, intensity=intensity))
    return items


def update_pattern_intensity(root: Path, config_name: str, rel_path: str, intensity: float) -> None:
    """Update intensity frontmatter in a thought-flow file."""
    target = _config_dir(root) / config_name / rel_path
    if not target.exists():
        raise FileNotFoundError(f"Pattern not found: {rel_path}")
    text = target.read_text(encoding="utf-8")
    updated = _update_frontmatter_intensity(text, intensity)
    target.write_text(updated, encoding="utf-8")


def _copy_analysis_patterns(root: Path, dest_config_dir: Path) -> list[Path]:
    """将 pattern.md 文件从 analysis/pattern/ 复制到目标配置目录。

    Source: analysis/pattern/{category}/{slug}/pattern.md
    Dest:   simulation_config/{name}/{category}/{slug}.md
    """
    src = root / _ANALYSIS_PATTERN_SRC
    copied: list[Path] = []
    for category in PATTERN_CATEGORIES:
        src_cat = src / category
        if not src_cat.exists():
            continue
        dst_cat = dest_config_dir / category
        dst_cat.mkdir(parents=True, exist_ok=True)
        for slug_dir in src_cat.iterdir():
            if not slug_dir.is_dir():
                continue
            pattern_file = slug_dir / "pattern.md"
            if not pattern_file.exists():
                continue
            dst = dst_cat / f"{slug_dir.name}.md"
            shutil.copy2(pattern_file, dst)
            copied.append(dst)
    return copied


def update_default_config(
    root: Path,
    emit: Callable[[str], None],
) -> None:
    """通过暂存目录原子更新 default_mode。

    先复制到暂存目录，生成思维流，然后通过三阶段 rename 交换：
      1. default_dir → .old   (原子)
      2. staging → default_dir (原子，失败则回滚 .old)
      3. 删除 .old
    这样在交换过程中 default_dir 始终存在，不会出现读取窗口。
    """
    cfg = _config_dir(root)
    default_dir = cfg / DEFAULT_CONFIG_NAME
    staging = cfg / ".default_mode.staging"
    old = cfg / ".default_mode.old"

    # 清理上次失败的暂存
    if staging.exists():
        shutil.rmtree(staging)

    try:
        copied = _copy_analysis_patterns(root, staging)
        generate_flows(copied, root, emit)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    # 三阶段原子交换
    if default_dir.exists():
        default_dir.rename(old)
    try:
        staging.rename(default_dir)
    except Exception:
        # 失败时恢复旧目录
        if old.exists():
            old.rename(default_dir)
        raise
    finally:
        if old.exists():
            shutil.rmtree(old)


def rename_config(root: Path, old_name: str, new_name: str) -> None:
    """Rename a config directory."""
    cfg_dir = _config_dir(root)
    old_path = cfg_dir / old_name
    new_path = cfg_dir / new_name
    if not old_path.exists():
        raise FileNotFoundError(f"Config not found: {old_name}")
    if new_path.exists():
        raise ValueError(f"Config already exists: {new_name}")
    old_path.rename(new_path)


def create_config(root: Path) -> str:
    """复制 default_mode → default_mode(N)。返回新配置名称。"""
    cfg_dir = _config_dir(root)
    default_dir = cfg_dir / DEFAULT_CONFIG_NAME
    if not default_dir.exists():
        raise ValueError("请先更新默认配置，再新建配置。")

    n = 1
    while (cfg_dir / f"{DEFAULT_CONFIG_NAME}({n})").exists():
        n += 1
    new_name = f"{DEFAULT_CONFIG_NAME}({n})"
    shutil.copytree(default_dir, cfg_dir / new_name)
    return new_name
