from dataclasses import dataclass
from pathlib import Path


@dataclass
class Skill:
    name: str
    description: str
    content: str
    source_root: Path
    source_file: Path


def _parse_skill_md(text: str) -> tuple[str, str, str]:
    """手动解析 frontmatter 格式，返回 (name, description, content)。"""
    if not text.startswith("---"):
        raise ValueError("SKILL.md 缺少 frontmatter 开头 ---")

    end = text.find("---", 3)
    if end == -1:
        raise ValueError("SKILL.md frontmatter 未正确关闭")

    frontmatter = text[3:end].strip()
    content = text[end + 3:].strip()

    name = ""
    description = ""
    for line in frontmatter.splitlines():
        if line.startswith("name:"):
            name = line[len("name:"):].strip()
        elif line.startswith("description:"):
            description = line[len("description:"):].strip()

    if not name:
        raise ValueError("SKILL.md frontmatter 缺少 name 字段")

    return name, description, content


def get_skill_root() -> Path:
    """默认 skill 根目录：library/agent_atoms/skills/skills。"""
    return Path(__file__).resolve().parent / "skills"


class SkillHub:
    """多路径 skill 索引中心。"""

    def __init__(self, roots: list[Path] | None = None):
        self.roots = roots[:] if roots else [get_skill_root()]
        self._skills: dict[str, Skill] = {}
        self.scan()

    def add_root(self, root: Path) -> None:
        if root not in self.roots:
            self.roots.append(root)

    def scan(self) -> None:
        self._skills = {}
        for root in self.roots:
            self._scan_root(root)

    def _scan_root(self, root: Path) -> None:
        if not root.exists():
            return
        for skill_dir in root.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            text = skill_file.read_text(encoding="utf-8")
            name, description, content = _parse_skill_md(text)
            self._skills[name] = Skill(
                name=name,
                description=description,
                content=content,
                source_root=root,
                source_file=skill_file,
            )

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_names(self) -> list[str]:
        return list(self._skills.keys())

    def get_descriptions(self) -> dict[str, str]:
        return {name: skill.description for name, skill in self._skills.items()}

    def get_content(self, name: str) -> str:
        skill = self.get(name)
        if not skill:
            return f"未找到 skill：{name}"
        return skill.content


class SkillRegistry:
    """给具体 chat-agent 使用的技能注册表（按 name 白名单注册）。"""

    def __init__(self, hub: SkillHub, names: list[str] | None = None):
        self.hub = hub
        self._names: list[str] = []
        self._name_set: set[str] = set()
        if names:
            self.register(names)

    def register(self, names: list[str]) -> None:
        for name in names:
            if name in self._name_set:
                continue
            if not self.hub.get(name):
                continue
            self._names.append(name)
            self._name_set.add(name)

    def list_names(self) -> list[str]:
        return self._names[:]

    def get_descriptions(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for name in self._names:
            skill = self.hub.get(name)
            if skill:
                result[name] = skill.description
        return result

    def get_content(self, name: str) -> str:
        if name not in self._name_set:
            return f"当前 chat-agent 未注册该 skill：{name}"
        skill = self.hub.get(name)
        if not skill:
            return f"未找到 skill：{name}"
        return skill.content

