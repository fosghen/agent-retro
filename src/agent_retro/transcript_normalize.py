"""Typed Codex content and tool-call normalization."""

from __future__ import annotations

import json
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
