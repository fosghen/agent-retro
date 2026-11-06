"""Typed transcript extraction and stable result composition."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from agent_retro.transcript_subagents import discover_subagents, match_subagents, project_agents

if TYPE_CHECKING:
    from agent_retro.transcript_io import JSONRecord
    from agent_retro.transcript_stream import StreamState


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
