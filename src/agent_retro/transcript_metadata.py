"""Typed bounded parsing helpers for transcript metadata."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping  # noqa: TC003 -- public types
from datetime import datetime
from typing import Any

from agent_retro.transcript_io import JSONRecord  # noqa: TC001 -- public return type


def extract_json_field(text: str, key: str) -> str | None:
    """Extract one JSON string field without parsing an incomplete buffer."""
    for pattern in (f'"{key}":"', f'"{key}": "'):
        index = text.find(pattern)
        if index < 0:
            continue
        start = index + len(pattern)
        cursor = start
        while cursor < len(text):
            if text[cursor] == "\\":
                cursor += 2
                continue
            if text[cursor] == '"':
                return text[start:cursor]
            cursor += 1
    return None


def buffered_jsonl_records(text: str) -> Iterator[JSONRecord]:
    """Yield complete JSON object records from one bounded text buffer."""
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            yield record


def is_injected_user_text(text: str) -> bool:
    """Identify environment and instruction text injected into user turns."""
    return text.lstrip().startswith(
        ("<system-reminder>", "<environment_context>", "# AGENTS.md instructions for ")
    )


def codex_prompt(records: Iterable[Mapping[str, Any]]) -> str | None:
    """Return the first bounded non-injected Codex user prompt."""
    for record in records:
        payload = record.get("payload") or {}
        if record.get("type") != "response_item" or payload.get("type") != "message":
            continue
        if payload.get("role") != "user":
            continue
        blocks = payload.get("content") or []
        text = "".join(block.get("text", "") for block in blocks if isinstance(block, dict)).strip()
        if text and not is_injected_user_text(text):
            return text[:200]
    return None


def parse_timestamp(value: object) -> datetime | None:
    """Parse one ISO 8601 timestamp, accepting a trailing UTC marker."""
    if not isinstance(value, str) or not value:
        return None
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def codex_metadata_lite(head: str, tail: str, size: int) -> JSONRecord:
    """Extract Codex metadata exclusively from bounded head and tail buffers."""
    records = [*buffered_jsonl_records(head), *buffered_jsonl_records(tail)]
    meta = next(
        (item.get("payload") or {} for item in records if item.get("type") == "session_meta"),
        {},
    )
    timestamps = [item.get("timestamp") for item in records if item.get("timestamp")]
    start_time = timestamps[0] if timestamps else meta.get("timestamp")
    end_time = timestamps[-1] if timestamps else start_time
    start, end = parse_timestamp(start_time), parse_timestamp(end_time)
    duration = round((end - start).total_seconds()) if start and end else None
    return {
        "session_id": meta.get("session_id") or meta.get("id"),
        "cwd": meta.get("cwd"),
        "git_branch": None,
        "version": meta.get("cli_version"),
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": duration,
        "file_size_bytes": size,
        "first_prompt": codex_prompt(records),
        "agent": "codex",
    }


def _last_timestamp(tail: str) -> str | None:
    for line in reversed(tail.splitlines()):
        timestamp = extract_json_field(line, "timestamp")
        if timestamp:
            return timestamp
    return extract_json_field(tail, "timestamp")


def _first_claude_prompt(head: str) -> str | None:
    for line in head.splitlines():
        if '"role":"user"' not in line and '"role": "user"' not in line:
            continue
        if '"tool_result"' in line:
            continue
        text = extract_json_field(line, "text")
        if text and not text.startswith("<system-reminder>"):
            return text[:200]
    return None


def _duration_seconds(start_time: object, end_time: object) -> int | None:
    start, end = parse_timestamp(start_time), parse_timestamp(end_time)
    return round((end - start).total_seconds()) if start and end else None
