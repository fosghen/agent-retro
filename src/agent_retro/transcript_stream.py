"""Typed streaming transcript accumulator."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from agent_retro.transcript_aggregate import (
    add_assistant_usage,
    empty_token_totals,
    result_size_bytes,
)
from agent_retro.transcript_conversation import assistant_arc_item, user_arc_item
from agent_retro.transcript_session import empty_session, record_session
from agent_retro.transcript_tools import record_tool_activity, tool_call_summary

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


def _process_block(state: StreamState, block: JSONRecord, role: object, timestamp: object) -> None:
    block_type = block.get("type")
    if block_type == "tool_use":
        tool_input = block.get("input") or {}
        call = tool_call_summary(block, timestamp)
        state.tool_calls.append(call)
        record_tool_activity(call, tool_input, state.files, state.commits, state.prs)
    elif block_type == "tool_result":
        tool_use_id = block.get("tool_use_id")
        if isinstance(tool_use_id, str) and tool_use_id:
            content = block.get("content", "")
            state.tool_result_sizes[tool_use_id] = result_size_bytes(content)
    elif block_type == "text":
        item = assistant_arc_item(block, role, timestamp)
        if item is not None:
            state.arc.append(item)


def process_record(state: StreamState, record: JSONRecord) -> None:
    """Accumulate one normalized transcript record."""
    record_session(state.session, record)
    branch = record.get("gitBranch")
    if isinstance(branch, str):
        state.branches.add(branch)
    timestamp = record.get("timestamp")
    message = record.get("message") or {}
    role = message.get("role")
    content = message.get("content", "")
    if add_assistant_usage(state.tokens, role, message.get("usage")):
        state.turn_count += 1
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                _process_block(state, block, role, timestamp)
    user_item = user_arc_item(content, role, timestamp)
    if user_item is not None:
        state.arc.append(user_item)
