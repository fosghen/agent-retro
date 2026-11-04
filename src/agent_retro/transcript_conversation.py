"""Typed conversation arc projection."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from agent_retro.transcript_io import JSONRecord

MIN_ASSISTANT_TEXT = 20
ASSISTANT_TEXT_LIMIT = 1000


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
