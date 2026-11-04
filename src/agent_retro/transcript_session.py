"""Typed streaming transcript session state."""

from typing import TypedDict


class SessionState(TypedDict):
    """Mutable session metadata accumulated from normalized records."""

    session_id: object
    cwd: object
    git_branch: object
    version: object
    start_time: object
    end_time: object
    duration_seconds: int | None
    branches_seen: set[str] | list[str]
    agent: str


def empty_session(agent: str) -> SessionState:
    """Create empty streaming session state for one transcript format."""
    return {
        "session_id": None,
        "cwd": None,
        "git_branch": None,
        "version": None,
        "start_time": None,
        "end_time": None,
        "duration_seconds": None,
        "branches_seen": set(),
        "agent": agent,
    }
