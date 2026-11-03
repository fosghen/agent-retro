"""Typed Codex content and tool-call normalization."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping  # noqa: TC003 -- public types
from typing import Any

from agent_retro.transcript_io import detect_transcript_format, stream_raw_jsonl

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


def _normalize_usage(payload: Mapping[str, Any], timestamp: object) -> JSONRecord:
    usage = json_object(payload.get("usage"))
    cached = usage.get("cached_input_tokens", 0) or 0
    total_input = usage.get("input_tokens", 0) or 0
    return {
        "timestamp": timestamp,
        "message": {
            "role": "assistant",
            "content": [],
            "usage": {
                "input_tokens": max(0, total_input - cached),
                "output_tokens": usage.get("output_tokens", 0) or 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": cached,
            },
        },
    }


def normalize_codex_record(record: Mapping[str, Any]) -> JSONRecord:  # noqa: PLR0911 -- variants
    """Normalize one Codex rollout record into the shared shape."""
    payload = json_object(record.get("payload"))
    timestamp = record.get("timestamp")
    if record.get("type") == "session_meta":
        return {
            "sessionId": payload.get("session_id") or payload.get("id"),
            "cwd": payload.get("cwd"),
            "version": payload.get("cli_version"),
            "timestamp": timestamp or payload.get("timestamp"),
        }
    if record.get("type") == "token_usage_record":
        return _normalize_usage(payload, timestamp)
    if record.get("type") != "response_item":
        return {"timestamp": timestamp}
    if payload.get("type") == "message":
        return {
            "timestamp": timestamp,
            "message": {
                "role": payload.get("role"),
                "content": normalize_codex_content(payload.get("content", [])),
            },
        }
    if payload.get("type") in ("custom_tool_call", "function_call"):
        return {
            "timestamp": timestamp,
            "message": {"role": "assistant", "content": [normalize_codex_tool(payload)]},
        }
    if payload.get("type") in ("custom_tool_call_output", "function_call_output"):
        return {
            "timestamp": timestamp,
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": payload.get("call_id", ""),
                        "content": payload.get("output", ""),
                    }
                ],
            },
        }
    return {"timestamp": timestamp}


def stream_normalized_jsonl(path: str) -> Iterator[JSONRecord]:
    """Yield normalized Codex records or unchanged Claude records."""
    transcript_format = detect_transcript_format(path)
    for record in stream_raw_jsonl(path):
        yield normalize_codex_record(record) if transcript_format == "codex" else record
