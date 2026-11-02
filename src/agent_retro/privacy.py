"""Privacy boundaries for derived retrospective data."""

from __future__ import annotations

import re
from pathlib import Path

_SECRET_VALUE = re.compile(r"(?i)\b(password|token)\s*[:=]\s*([^\s]+)")
_BEARER_VALUE = re.compile(r"(?i)(authorization\s*:\s*bearer)\s+([^\s]+)")
DEFAULT_EXCERPT_LIMIT = 500


def redact_excerpt(text: str, limit: int = DEFAULT_EXCERPT_LIMIT) -> str:
    """Remove common credentials and return a bounded evidence excerpt."""
    if limit < 1:
        message = "excerpt limit must be positive"
        raise ValueError(message)
    redacted = _SECRET_VALUE.sub(r"\1=[REDACTED]", text)
    redacted = _BEARER_VALUE.sub(r"\1 [REDACTED]", redacted)
    if len(redacted) <= limit:
        return redacted
    return f"{redacted[: limit - 1]}…"


def delete_derived(state_root: Path, relative_path: Path) -> None:
    """Delete one derived file without crossing the local state boundary."""
    root = state_root.resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        message = "derived artifact must remain below the state root"
        raise ValueError(message)
    if candidate.is_dir():
        message = "directory deletion is not supported"
        raise ValueError(message)
    candidate.unlink(missing_ok=True)
