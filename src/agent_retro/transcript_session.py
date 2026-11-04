"""Typed streaming transcript session state."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from agent_retro.transcript_metadata import parse_timestamp

if TYPE_CHECKING:
    from agent_retro.transcript_io import JSONRecord


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


def record_session(session: SessionState, record: JSONRecord) -> None:
    """Accumulate session metadata from one normalized record."""
    if record.get("sessionId") and not session["session_id"]:
        session["session_id"] = record["sessionId"]
    if record.get("cwd") and not session["cwd"]:
        session["cwd"] = record["cwd"]
    if record.get("version") and not session["version"]:
        session["version"] = record["version"]
    branch = record.get("gitBranch")
    branches = session["branches_seen"]
    if isinstance(branch, str):
        if not session["git_branch"]:
            session["git_branch"] = branch
        if isinstance(branches, set):
            branches.add(branch)
    timestamp = record.get("timestamp")
    if timestamp:
        if not session["start_time"]:
            session["start_time"] = timestamp
        session["end_time"] = timestamp


def finalize_session(session: SessionState) -> None:
    """Finalize duration and deterministically order observed branches."""
    start = parse_timestamp(session["start_time"])
    end = parse_timestamp(session["end_time"])
    if start and end:
        session["duration_seconds"] = round((end - start).total_seconds())
    session["branches_seen"] = sorted(session["branches_seen"])
