r"""
命令注册与匹配系统。

## 核心设计：Hub / Registry 双层模式

  Hub（全局定义中心）        Registry（Agent 白名单）       Command（用户触发入口）
  ┌─────────────────┐       ┌──────────────────┐        ┌──────────────────────┐
  │ 存所有 Command   │ ←─── │ 按名字引用 Hub    │ ←────  │ 用户输入 /xxx        │
  │ Definition       │       │ 中的定义          │        │ 触发后临时注入       │
  └─────────────────┘       └──────────────────┘        │ skill/tool 到本轮    │
                                                        └──────────────────────┘
  与 ToolHub/ToolRegistry、SkillHub/SkillRegistry 完全对称。

  Command 与普通 tool/skill 的关键区别：
  - Command 的主动权在用户，由用户通过 /命令 手动触发
  - Agent 一开始并不知道 command 相关 tools 和 skills 的存在
  - 只有当用户显式输入 /命令 后，系统才将对应的资源注入本轮对话
"""

from dataclasses import dataclass
import warnings


@dataclass(frozen=True)
class CommandDefinition:
    name: str
    skill_names: tuple[str, ...]
    tool_names: tuple[str, ...]


@dataclass(frozen=True)
class CommandMatch:
    command: str
    skill_names: list[str]
    tool_names: list[str]


class CommandHub:
    """程序化 command 索引中心，与 ToolHub / SkillHub 对称。"""

    def __init__(self):
        self._commands: dict[str, CommandDefinition] = {}

    def register(self, definition: CommandDefinition) -> None:
        self._commands[definition.name] = definition

    def get(self, name: str) -> CommandDefinition | None:
        return self._commands.get(name)

    def list_names(self) -> list[str]:
        return list(self._commands.keys())


class CommandRegistry:
    """给具体 agent 使用的命令白名单（按 name 注册）。"""

    def __init__(self, hub: CommandHub, names: list[str] | None = None):
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
                warnings.warn(
                    f"CommandRegistry: 跳过未在 CommandHub 中注册的命令 '{name}'"
                    f"——请确认 CommandHub.register() 已先调用"
                )
                continue
            self._names.append(name)
            self._name_set.add(name)

    def list_names(self) -> list[str]:
        return self._names[:]

    def match(self, user_input: str) -> CommandMatch | None:
        if not user_input.startswith("/"):
            return None
        cmd = user_input.split(" ", 1)[0]
        if cmd not in self._name_set:
            return None
        definition = self.hub.get(cmd)
        if definition is None:
            return None
        return CommandMatch(
            command=definition.name,
            skill_names=list(definition.skill_names),
            tool_names=list(definition.tool_names),
        )

    def all_skill_names(self) -> set[str]:
        names: set[str] = set()
        for name in self._names:
            definition = self.hub.get(name)
            if definition:
                names.update(definition.skill_names)
        return names

    def all_tool_names(self) -> set[str]:
        names: set[str] = set()
        for name in self._names:
            definition = self.hub.get(name)
            if definition:
                names.update(definition.tool_names)
        return names
