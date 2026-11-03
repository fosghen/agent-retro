"""Typed bounded parsing helpers for transcript metadata."""

from __future__ import annotations

import json
from collections.abc import Iterator  # noqa: TC003 -- public return type

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
