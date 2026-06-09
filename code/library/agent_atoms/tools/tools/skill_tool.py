from code.library.agent_atoms.skills.skills_loader import SkillHub
from code.library.agent_atoms.tools.tool_def import Tool


def make_load_skill_tool(hub: SkillHub) -> Tool:
    def fn(name: str) -> str:
        return hub.get_content(name)

    return Tool(
        name="load_skill",
        description="获取指定名称的 skill 完整内容。",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "skill 名称"},
            },
            "required": ["name"],
        },
        fn=fn,
    )
