"""Typed subagent transcript loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

from agent_retro.transcript_aggregate import (
    add_assistant_usage,
    empty_token_totals,
    estimated_cost,
)
from agent_retro.transcript_metadata import parse_timestamp
from agent_retro.transcript_normalize import stream_normalized_jsonl

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import datetime

    from agent_retro.transcript_aggregate import TokenTotals
    from agent_retro.transcript_io import JSONRecord


class SubagentInfo(TypedDict):
    """Accounting metadata derived from one subagent transcript."""

    file: str
    tokens: TokenTotals
    cost: float
    start_time: datetime | None
    meta: object | None


def load_subagent(path: Path) -> SubagentInfo:
    """Load accounting metadata from one normalized subagent transcript."""
    tokens = empty_token_totals()
    start_time = None
    for record in stream_normalized_jsonl(str(path)):
        message = record.get("message") or {}
        add_assistant_usage(tokens, message.get("role"), message.get("usage"))
        if start_time is None:
            start_time = parse_timestamp(record.get("timestamp"))
    meta_path = path.with_suffix(".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else None
    return {
        "file": path.name,
        "tokens": tokens,
        "cost": round(estimated_cost(tokens) or 0.0, 4),
        "start_time": start_time,
        "meta": meta,
    }


def discover_subagents(directory: str | Path) -> list[SubagentInfo]:
    """Load subagent transcripts in deterministic filename order."""
    return [load_subagent(path) for path in sorted(Path(directory).glob("*.jsonl"))]


def project_agents(tool_calls: Iterable[Mapping[str, Any]]) -> list[JSONRecord]:
    """Project Agent tool calls into the stable result schema."""
    agents = []
    for call in tool_calls:
        if call.get("name") != "Agent":
            continue
        agent = {
            "description": call.get("agent_description", ""),
            "type": call.get("agent_type", "") or "general-purpose",
            "model": call.get("agent_model", "") or "inherited",
            "prompt_preview": call.get("agent_prompt_preview", ""),
            "background": call.get("run_in_background", False),
            "timestamp": call.get("timestamp"),
            "tool_use_id": call.get("tool_use_id", ""),
            "tokens": None,
            "estimated_cost_usd": None,
        }
        if "result_size_bytes" in call:
            agent["result_size_bytes"] = call["result_size_bytes"]
        agents.append(agent)
    return agents
