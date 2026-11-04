"""Typed conversation arc projection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from agent_retro.transcript_metadata import is_injected_user_text

if TYPE_CHECKING:
    from typing import Any

    from agent_retro.transcript_io import JSONRecord

MIN_ASSISTANT_TEXT = 20
ASSISTANT_TEXT_LIMIT = 1000
USER_TEXT_LIMIT = 2000


def assistant_arc_item(
    block: Mapping[str, Any], role: object, timestamp: object
) -> JSONRecord | None:
    """Project one meaningful assistant text block into the conversation arc."""
    text = block.get("text", "")
    if role != "assistant" or not isinstance(text, str):
        return None
    text = text.strip()
    if len(text) <= MIN_ASSISTANT_TEXT:
        return None
    return {"role": "assistant", "text": text[:ASSISTANT_TEXT_LIMIT], "timestamp": timestamp}


def user_arc_item(content: object, role: object, timestamp: object) -> JSONRecord | None:
    """Project one non-injected user message into the conversation arc."""
    if role != "user":
        return None
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, Mapping) and block.get("type") == "text":
                value = block.get("text", "")
                if isinstance(value, str):
                    parts.append(value)
        text = "".join(parts)
    else:
        return None
    text = text.strip()
    if not text or is_injected_user_text(text):
        return None
    return {"role": "user", "text": text[:USER_TEXT_LIMIT], "timestamp": timestamp}
