"""Typed, bounded transcript input primitives."""

from __future__ import annotations

import json
from collections.abc import Iterator  # noqa: TC003 -- public return type
from pathlib import Path
from typing import Any, Literal

type JSONRecord = dict[str, Any]
type TranscriptFormat = Literal["claude", "codex"]
LITE_READ_BUF_SIZE = 65536


def stream_raw_jsonl(path: str | Path) -> Iterator[JSONRecord]:
    """Yield JSON object records lazily, skipping malformed or non-object lines."""
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


def detect_transcript_format(path: str | Path) -> TranscriptFormat:
    """Detect Codex metadata or default to the Claude transcript shape."""
    for record in stream_raw_jsonl(path):
        if record.get("type") == "session_meta" and isinstance(record.get("payload"), dict):
            return "codex"
        return "claude"
    return "claude"


def read_head_tail(path: str | Path) -> tuple[str, str, int]:
    """Read at most 64 KiB from each end of one transcript."""
    transcript = Path(path)
    size = transcript.stat().st_size
    with transcript.open("rb") as handle:
        head = handle.read(LITE_READ_BUF_SIZE).decode("utf-8", errors="replace")
        if size <= LITE_READ_BUF_SIZE:
            return head, head, size
        handle.seek(max(0, size - LITE_READ_BUF_SIZE))
        tail = handle.read(LITE_READ_BUF_SIZE).decode("utf-8", errors="replace")
    return head, tail, size
