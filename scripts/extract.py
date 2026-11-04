#!/usr/bin/env python3
"""
Extract structured data from a Claude Code session transcript (JSONL).

Usage:
    python extract.py <session-jsonl-path> [--subagents-dir <path>] [--summary] [--metadata-only]

Outputs JSON to stdout. Use --summary for a compact version that omits
individual tool call details (just counts and key events).
Use --metadata-only for cheap session verification (head/tail read only).
"""

import json
import sys
import os
from collections import defaultdict
from pathlib import Path

from agent_retro.transcript_aggregate import (
    PRICE_PER_M,
    PRICING_LAST_VERIFIED,
    add_assistant_usage,
    attach_result_sizes,
    empty_token_totals,
    estimated_cost,
    result_size_bytes,
    result_size_stats,
)
from agent_retro.transcript_conversation import assistant_arc_item, user_arc_item
from agent_retro.transcript_io import (
    LITE_READ_BUF_SIZE,
    detect_transcript_format,
    read_head_tail,
    stream_raw_jsonl,
)
from agent_retro.transcript_metadata import (
    extract_json_field,
    extract_metadata_lite as _typed_metadata_lite,
    is_injected_user_text as _is_injected_user_text,
    parse_timestamp as parse_ts,
)
from agent_retro.transcript_normalize import stream_normalized_jsonl as stream_jsonl
from agent_retro.transcript_session import empty_session, finalize_session, record_session
from agent_retro.transcript_stream import new_stream_state, process_record
from agent_retro.transcript_subagents import discover_subagents, project_agents
from agent_retro.transcript_subagents import match_subagents
from agent_retro.transcript_tools import (
    record_tool_activity,
    skill_summaries,
    tool_call_summary,
    tool_result_view,
)

SCHEMA_VERSION = "0.1.0"


def extract_metadata_lite(path):
    """Extract bounded session metadata through the typed compatibility boundary."""
    return _typed_metadata_lite(path)


def extract_all_streaming(jsonl_path, subagents_dir=None, summary_mode=False):
    """Main extraction pipeline using streaming — processes line-by-line."""

    transcript_format = detect_transcript_format(jsonl_path)

    state = new_stream_state(transcript_format)
    session = state.session
    tokens_total = state.tokens
    turn_count = 0
    tool_calls = state.tool_calls
    tool_result_sizes = state.tool_result_sizes
    arc = state.arc
    branches = state.branches
    commits = state.commits
    prs = state.prs
    files = state.files

    for rec in stream_jsonl(jsonl_path):
        process_record(state, rec)
    turn_count = state.turn_count

    # --- Post-processing ---

    finalize_session(session)

    # Compute cost
    cost = estimated_cost(tokens_total, transcript_format)

    attach_result_sizes(tool_calls, tool_result_sizes)
    result_size_summary = result_size_stats(tool_calls)

    # Extract agents
    agents = _extract_agents(tool_calls, subagents_dir)

    # Warn if agents exist but have no cost data (subagents_dir missing)
    agents_without_cost = [a for a in agents if a.get("estimated_cost_usd") is None
                           and a.get("description") and not a.get("description", "").startswith("[unmatched")]
    if agents_without_cost:
        print(f"Warning: {len(agents_without_cost)} agent dispatch(es) have no subagent cost data. "
              f"Pass --subagents-dir <path> to attribute subagent costs.",
              file=sys.stderr)

    # Build result
    result = {
        "schema_version": SCHEMA_VERSION,
        "session": session,
        "tokens": {
            "total": tokens_total,
            "turn_count": turn_count,
            "estimated_cost_usd": round(cost, 4) if cost is not None else None,
        },
        "agents": agents,
        "skills": skill_summaries(tool_calls),
        "git": {
            "branches": sorted(branches),
            "commits": commits,
            "pr_operations": prs,
        },
        "files": {k: sorted(v) for k, v in files.items()},
        "conversation_arc": arc,
        "tool_result_sizes": result_size_summary,
        "tools": tool_result_view(tool_calls, summary=summary_mode),
    }

    return result


def _extract_agents(tool_calls, subagents_dir=None):
    """Extract agent dispatch details and match with subagent JSONL files."""
    agents = project_agents(tool_calls)

    if subagents_dir and os.path.isdir(subagents_dir):
        _match_subagent_files(agents, subagents_dir)

    return agents


def _match_subagent_files(agents, subagents_dir):
    """Match subagent JSONL files to dispatches using timestamp proximity."""
    match_subagents(agents, discover_subagents(subagents_dir))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract.py <session.jsonl> [--subagents-dir <path>] [--summary] [--metadata-only]")
        sys.exit(1)

    jsonl_path = sys.argv[1]
    subagents_dir = None
    summary_mode = "--summary" in sys.argv
    metadata_only = "--metadata-only" in sys.argv

    if metadata_only:
        result = extract_metadata_lite(jsonl_path)
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)

    if "--subagents-dir" in sys.argv:
        idx = sys.argv.index("--subagents-dir")
        if idx + 1 < len(sys.argv):
            subagents_dir = sys.argv[idx + 1]
    else:
        # Auto-detect: look for sibling directory with same name as the JSONL
        stem = Path(jsonl_path).stem
        candidate = Path(jsonl_path).parent / stem / "subagents"
        if candidate.is_dir():
            subagents_dir = str(candidate)

    result = extract_all_streaming(jsonl_path, subagents_dir, summary_mode)
    print(json.dumps(result, indent=2, default=str))
