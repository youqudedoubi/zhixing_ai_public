from code.backend.services.chat_agent.command.registry import CommandMatch, CommandRegistry


def parse_command(
    user_input: str,
    registry: CommandRegistry,
) -> tuple[str | None, list[str], list[str]]:
    """解析用户输入中的 slash 命令，返回 (命令名, 附加 skills, 附加 tools)。"""
    match = registry.match(user_input)
    if match is None:
        return None, [], []
    return match.command, match.skill_names, match.tool_names


def parse_command_match(user_input: str, registry: CommandRegistry) -> CommandMatch | None:
    return registry.match(user_input)
