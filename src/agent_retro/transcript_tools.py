"""Typed tool-call projection."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


def _secondary_fields(name: str, tool_input: Mapping[str, Any]) -> JSONRecord:
    if name in {"TaskCreate", "TaskUpdate", "TaskList", "TaskOutput"}:
        return {
            "task_detail": {
                key: value
                for key, value in tool_input.items()
                if key in {"description", "status", "id"}
            }
        }
    if name == "AskUserQuestion":
        questions = tool_input.get("questions", [])
        return {
            "questions": [
                item.get("question", "") for item in questions if isinstance(item, Mapping)
            ]
        }
    if name.startswith("mcp__"):
        return {"mcp_inputs_preview": json.dumps(tool_input)[:PREVIEW_LIMIT]}
    return {}


def tool_call_summary(block: Mapping[str, Any], timestamp: object) -> JSONRecord:
    """Project one tool-use block into the stable call summary schema."""
    raw_name = block.get("name", "unknown")
    name = raw_name if isinstance(raw_name, str) else "unknown"
    raw_input = block.get("input", {})
    tool_input = raw_input if isinstance(raw_input, Mapping) else {}
    summary: JSONRecord = {
        "name": name,
        "timestamp": timestamp,
        "tool_use_id": block.get("id", ""),
    }
    summary.update(_primary_fields(name, tool_input) or _secondary_fields(name, tool_input))
    return summary
