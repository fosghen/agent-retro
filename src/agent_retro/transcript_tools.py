"""Typed tool-call projection."""

from __future__ import annotations

import json
from collections import Counter
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


def record_tool_activity(
    call: JSONRecord,
    tool_input: Mapping[str, Any],
    files: dict[str, set[str]],
    commits: list[JSONRecord],
    prs: list[JSONRecord],
) -> None:
    """Record file and git activity for one projected tool call."""
    name = call.get("name")
    file_path = tool_input.get("file_path")
    categories = {"Read": "read", "Write": "written", "Edit": "edited"}
    if isinstance(name, str) and isinstance(file_path, str) and file_path:
        category = categories.get(name)
        if category is not None:
            files.setdefault(category, set()).add(file_path)
    if name not in {"Bash", "exec", "exec_command"}:
        return
    command = tool_input.get("command")
    if not isinstance(command, str):
        return
    activity = {"command": command[:200], "timestamp": call.get("timestamp")}
    if "git commit" in command:
        commits.append(activity)
    if "gh pr" in command:
        prs.append(activity)


def skill_summaries(tool_calls: list[JSONRecord]) -> list[JSONRecord]:
    """Project Skill calls into the stable top-level skill schema."""
    return [
        {
            "name": call.get("skill_name", ""),
            "args": call.get("skill_args", ""),
            "timestamp": call.get("timestamp"),
        }
        for call in tool_calls
        if call.get("name") == "Skill"
    ]


def tool_result_view(tool_calls: list[JSONRecord], *, summary: bool) -> JSONRecord:
    """Build deterministic summary or full tool output."""
    counts = Counter(str(call.get("name", "unknown")) for call in tool_calls)
    result: JSONRecord = {
        "counts": dict(counts.most_common()),
        "total_calls": len(tool_calls),
    }
    if not summary:
        result["calls"] = tool_calls
    return result
