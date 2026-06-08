from datetime import datetime

from code.backend.models.schemas import Message, ModifiedFile
from code.backend.services.chat_agent.tools.pattern_events import sort_pattern_events
from code.backend.services.workspace.checkpoint import get_modified_files


def collect_modified_files(checkpoint_sha: str) -> list[ModifiedFile]:
    return [
        ModifiedFile(
            path=file_change["path"],
            change_type=file_change["change_type"],
            pre_content=file_change["pre_content"],
            post_content=file_change["post_content"],
        )
        for file_change in get_modified_files(checkpoint_sha)
    ]


def append_action_messages(
    new_messages: list[Message],
    modified_files: list[ModifiedFile],
    pattern_events: list[dict],
) -> None:
    if modified_files:
        new_messages.append(
            Message(
                role="action",
                timestamp=datetime.now().isoformat(),
                content="",
                action_type="file_change",
                action_status="completed",
                action_data={"files": [m.model_dump() for m in modified_files]},
            )
        )

    if pattern_events:
        new_messages.append(
            Message(
                role="action",
                timestamp=datetime.now().isoformat(),
                content="",
                action_type="pattern_score_change",
                action_status="completed",
                action_data={"events": sort_pattern_events(pattern_events)},
            )
        )
