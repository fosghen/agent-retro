"""Pure validation for issue-backed puzzle markers."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

TOKEN = re.compile(r"\b(?:TODO|FIXME)\b")
MARKER = re.compile(
    r"\b(?:TODO|FIXME)\(#(?P<issue>[1-9]\d*), estimate:(?P<amount>[1-9]\d*)"
    r"(?P<unit>[mhd])\): (?P<explanation>\S.{9,})$"
)
MINUTES = {"m": 1, "h": 60, "d": 1440}
MAX_ESTIMATE_MINUTES = 30 * MINUTES["d"]
IssueCheck = Callable[[int], bool]


def validate_text(text: str, path: Path, issue_is_open: IssueCheck) -> tuple[str, ...]:
    """Return actionable violations in one maintained executable file."""
    errors: list[str] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        tokens = list(TOKEN.finditer(line))
        if not tokens:
            continue
        marker = MARKER.search(line)
        valid_shape = (
            marker is not None and marker.start() == tokens[0].start() and len(tokens) == 1
        )
        if not valid_shape:
            errors.append(_error(path, line_number, "use TODO(#123, estimate:2h): explanation"))
            continue
        amount = int(marker.group("amount"))
        if amount * MINUTES[marker.group("unit")] > MAX_ESTIMATE_MINUTES:
            errors.append(_error(path, line_number, "estimate must not exceed 30d"))
        elif not issue_is_open(int(marker.group("issue"))):
            errors.append(_error(path, line_number, "referenced GitHub issue must be open"))
    return tuple(errors)


def _error(path: Path, line_number: int, remediation: str) -> str:
    return f"{path}:{line_number}: puzzle marker invalid; {remediation}"
