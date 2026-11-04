"""Typed subagent transcript loading."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from datetime import datetime

    from agent_retro.transcript_aggregate import TokenTotals


class SubagentInfo(TypedDict):
    """Accounting metadata derived from one subagent transcript."""

    file: str
    tokens: TokenTotals
    cost: float
    start_time: datetime | None
    meta: object | None
