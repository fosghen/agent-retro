"""Typed streaming transcript accumulator."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from agent_retro.transcript_aggregate import empty_token_totals
from agent_retro.transcript_session import empty_session

if TYPE_CHECKING:
    from agent_retro.transcript_aggregate import TokenTotals
    from agent_retro.transcript_io import JSONRecord
    from agent_retro.transcript_session import SessionState


@dataclass
class StreamState:
    """Mutable state accumulated during one streaming transcript pass."""

    session: SessionState
    tokens: TokenTotals = field(default_factory=empty_token_totals)
    turn_count: int = 0
    tool_calls: list[JSONRecord] = field(default_factory=list)
    tool_result_sizes: dict[str, int] = field(default_factory=dict)
    arc: list[JSONRecord] = field(default_factory=list)
    branches: set[str] = field(default_factory=set)
    commits: list[JSONRecord] = field(default_factory=list)
    prs: list[JSONRecord] = field(default_factory=list)
    files: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))


def new_stream_state(agent: str) -> StreamState:
    """Create empty state for one detected transcript format."""
    return StreamState(session=empty_session(agent))
