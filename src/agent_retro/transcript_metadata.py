"""Typed bounded parsing helpers for transcript metadata."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping  # noqa: TC003 -- public types
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
        text = "".join(
            block.get("text", "") for block in blocks if isinstance(block, dict)
        ).strip()
        if text and not is_injected_user_text(text):
            return text[:200]
    return None
