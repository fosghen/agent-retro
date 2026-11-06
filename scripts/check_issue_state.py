"""Require a publication branch to reference one open GitHub issue."""

from __future__ import annotations

import json


class IssueStateError(ValueError):
    """The referenced issue is absent or unavailable for development."""


def check(number: int, payload: str) -> None:
    """Validate one live issue response."""
    issue = json.loads(payload)
    if issue.get("number") != number:
        message = f"issue #{number} is absent"
        raise IssueStateError(message)
    if issue.get("state") != "OPEN":
        message = f"issue #{number} must be open"
        raise IssueStateError(message)
