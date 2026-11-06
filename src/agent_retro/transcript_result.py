"""Typed transcript extraction and stable result composition."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from agent_retro.transcript_aggregate import attach_result_sizes, estimated_cost, result_size_stats
from agent_retro.transcript_io import detect_transcript_format
from agent_retro.transcript_normalize import stream_normalized_jsonl
from agent_retro.transcript_session import finalize_session
from agent_retro.transcript_stream import new_stream_state, process_record
from agent_retro.transcript_subagents import discover_subagents, match_subagents, project_agents
from agent_retro.transcript_tools import skill_summaries, tool_result_view

if TYPE_CHECKING:
    from agent_retro.transcript_io import JSONRecord
    from agent_retro.transcript_stream import StreamState

SCHEMA_VERSION = "0.1.0"


def _agents(state: StreamState, subagents_dir: str | Path | None) -> list[JSONRecord]:
    agents = project_agents(state.tool_calls)
    if subagents_dir is not None and Path(subagents_dir).is_dir():
        match_subagents(agents, discover_subagents(subagents_dir))
    missing = [
        agent
        for agent in agents
        if agent.get("estimated_cost_usd") is None
        and agent.get("description")
        and not str(agent.get("description", "")).startswith("[unmatched")
    ]
    if missing:
        sys.stderr.write(
            f"Warning: {len(missing)} agent dispatch(es) have no subagent cost data. "
            "Pass --subagents-dir <path> to attribute subagent costs.\n"
        )
    return agents


def compose_result(
    state: StreamState, *, subagents_dir: str | Path | None = None, summary: bool = False
) -> JSONRecord:
    """Finalize accumulated state and compose the stable extraction schema."""
    finalize_session(state.session)
    attach_result_sizes(state.tool_calls, state.tool_result_sizes)
    cost = estimated_cost(state.tokens, str(state.session["agent"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "session": state.session,
        "tokens": {
            "total": state.tokens,
            "turn_count": state.turn_count,
            "estimated_cost_usd": round(cost, 4) if cost is not None else None,
        },
        "agents": _agents(state, subagents_dir),
        "skills": skill_summaries(state.tool_calls),
        "git": {
            "branches": sorted(state.branches),
            "commits": state.commits,
            "pr_operations": state.prs,
        },
        "files": {key: sorted(paths) for key, paths in state.files.items()},
        "conversation_arc": state.arc,
        "tool_result_sizes": result_size_stats(state.tool_calls),
        "tools": tool_result_view(state.tool_calls, summary=summary),
    }


def extract_transcript(
    path: str | Path, *, subagents_dir: str | Path | None = None, summary: bool = False
) -> JSONRecord:
    """Stream one transcript and return its stable extraction result."""
    transcript_format = detect_transcript_format(path)
    state = new_stream_state(transcript_format)
    for record in stream_normalized_jsonl(str(path)):
        process_record(state, record)
    return compose_result(state, subagents_dir=subagents_dir, summary=summary)
