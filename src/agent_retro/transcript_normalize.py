"""Typed Codex content and tool-call normalization."""

from __future__ import annotations

import json
from collections.abc import Mapping  # noqa: TC003 -- public input type
from typing import Any

JSONRecord = dict[str, Any]


def normalize_codex_content(content: object) -> object:
    """Convert Codex text blocks to the shared text-block shape."""
    if not isinstance(content, list):
        return content
    normalized: list[JSONRecord] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") in ("input_text", "output_text", "text"):
            normalized.append({"type": "text", "text": block.get("text", "")})
    return normalized


def json_object(value: object) -> JSONRecord:
    """Decode a JSON object, returning an empty object for invalid input."""
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def normalize_codex_tool(payload: Mapping[str, Any]) -> JSONRecord:
    """Normalize Codex custom, function, and agent tool calls."""
    name = payload.get("name", "unknown")
    if payload.get("type") == "custom_tool_call":
        tool_input = {"command": payload.get("input", "")}
    else:
        tool_input = json_object(payload.get("arguments"))
    if isinstance(name, str) and name.endswith("spawn_agent"):
        name = "Agent"
        tool_input = {
            "description": tool_input.get("task_name", ""),
            "subagent_type": tool_input.get("task_name", ""),
            "model": tool_input.get("model", ""),
            "prompt": tool_input.get("message", ""),
        }
    return {
        "type": "tool_use",
        "id": payload.get("call_id", ""),
        "name": name,
        "input": tool_input,
    }
