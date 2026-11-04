"""Typed tool-call projection."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from agent_retro.transcript_io import JSONRecord

PREVIEW_LIMIT = 300


def _primary_fields(name: str, tool_input: Mapping[str, Any]) -> JSONRecord:
    fields: JSONRecord = {}
    if name == "Agent":
        fields.update(
            agent_description=tool_input.get("description", ""),
            agent_type=tool_input.get("subagent_type", ""),
            agent_model=tool_input.get("model", ""),
            agent_prompt_preview=str(tool_input.get("prompt", ""))[:PREVIEW_LIMIT],
            run_in_background=tool_input.get("run_in_background", False),
        )
    elif name == "Skill":
        fields.update(skill_name=tool_input.get("skill", ""), skill_args=tool_input.get("args", ""))
    elif name in {"Bash", "exec", "exec_command"}:
        fields["command"] = str(tool_input.get("command", ""))[:PREVIEW_LIMIT]
    elif name in {"Read", "Write", "Edit"}:
        fields["file_path"] = tool_input.get("file_path", "")
    elif name in {"Grep", "Glob"}:
        fields["pattern"] = tool_input.get("pattern", "")
    return fields
