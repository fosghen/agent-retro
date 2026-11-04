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
from collections import Counter, defaultdict
from pathlib import Path

from agent_retro.transcript_aggregate import (
    PRICE_PER_M,
    PRICING_LAST_VERIFIED,
    add_assistant_usage,
    empty_token_totals,
    estimated_cost,
)
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
from agent_retro.transcript_subagents import discover_subagents

SCHEMA_VERSION = "0.1.0"


def extract_metadata_lite(path):
    """Extract bounded session metadata through the typed compatibility boundary."""
    return _typed_metadata_lite(path)


def extract_all_streaming(jsonl_path, subagents_dir=None, summary_mode=False):
    """Main extraction pipeline using streaming — processes line-by-line."""

    transcript_format = detect_transcript_format(jsonl_path)

    # Session metadata
    session = {
        "session_id": None,
        "cwd": None,
        "git_branch": None,
        "version": None,
        "start_time": None,
        "end_time": None,
        "duration_seconds": None,
        "branches_seen": set(),
        "agent": transcript_format,
    }

    # Token totals
    tokens_total = empty_token_totals()
    turn_count = 0

    # Tool tracking
    tool_calls = []
    tool_counts = Counter()
    total_tool_calls = 0

    # Tool result sizes (tool_use_id -> size in bytes)
    tool_result_sizes = {}

    # Conversation arc
    arc = []

    # Git tracking
    branches = set()
    commits = []
    prs = []

    # File tracking
    files = defaultdict(set)

    for rec in stream_jsonl(jsonl_path):
        # --- Session metadata ---
        if rec.get("sessionId") and not session["session_id"]:
            session["session_id"] = rec["sessionId"]
        if rec.get("cwd") and not session["cwd"]:
            session["cwd"] = rec["cwd"]
        if rec.get("gitBranch"):
            if not session["git_branch"]:
                session["git_branch"] = rec["gitBranch"]
            session["branches_seen"].add(rec["gitBranch"])
            branches.add(rec["gitBranch"])
        if rec.get("version") and not session["version"]:
            session["version"] = rec["version"]

        ts = rec.get("timestamp")
        if ts:
            if not session["start_time"]:
                session["start_time"] = ts
            session["end_time"] = ts

        msg = rec.get("message", {})
        role = msg.get("role")
        content = msg.get("content", "")
        usage = msg.get("usage", {})

        # --- Token usage (assistant messages only) ---
        if add_assistant_usage(tokens_total, role, usage):
            turn_count += 1

        # --- Process content blocks ---
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue

                block_type = block.get("type")

                # Tool use blocks (assistant calling tools)
                if block_type == "tool_use":
                    name = block.get("name", "unknown")
                    tool_input = block.get("input", {})
                    tool_counts[name] += 1
                    total_tool_calls += 1

                    call_summary = {
                        "name": name,
                        "timestamp": ts,
                        "tool_use_id": block.get("id", ""),
                    }

                    if name == "Agent":
                        call_summary["agent_description"] = tool_input.get("description", "")
                        call_summary["agent_type"] = tool_input.get("subagent_type", "")
                        call_summary["agent_model"] = tool_input.get("model", "")
                        call_summary["agent_prompt_preview"] = tool_input.get("prompt", "")[:300]
                        call_summary["run_in_background"] = tool_input.get("run_in_background", False)
                    elif name == "Skill":
                        call_summary["skill_name"] = tool_input.get("skill", "")
                        call_summary["skill_args"] = tool_input.get("args", "")
                    elif name in ("Bash", "exec", "exec_command"):
                        call_summary["command"] = tool_input.get("command", "")[:300]
                    elif name in ("Read", "Write", "Edit"):
                        call_summary["file_path"] = tool_input.get("file_path", "")
                    elif name in ("Grep", "Glob"):
                        call_summary["pattern"] = tool_input.get("pattern", "")
                    elif name in ("TaskCreate", "TaskUpdate", "TaskList", "TaskOutput"):
                        call_summary["task_detail"] = {
                            k: v for k, v in tool_input.items()
                            if k in ("description", "status", "id")
                        }
                    elif name == "AskUserQuestion":
                        questions = tool_input.get("questions", [])
                        call_summary["questions"] = [q.get("question", "") for q in questions]
                    elif name.startswith("mcp__"):
                        call_summary["mcp_inputs_preview"] = json.dumps(tool_input)[:300]

                    tool_calls.append(call_summary)

                    # Track files
                    fp = tool_input.get("file_path", "")
                    if fp:
                        if name == "Read":
                            files["read"].add(fp)
                        elif name == "Write":
                            files["written"].add(fp)
                        elif name == "Edit":
                            files["edited"].add(fp)

                    # Track git activity from bash commands
                    if name in ("Bash", "exec", "exec_command"):
                        cmd = tool_input.get("command", "")
                        if "git commit" in cmd:
                            commits.append({"command": cmd[:200], "timestamp": ts})
                        if "gh pr" in cmd:
                            prs.append({"command": cmd[:200], "timestamp": ts})

                # Tool result blocks — capture SIZE only, not content
                elif block_type == "tool_result":
                    tool_use_id = block.get("tool_use_id", "")
                    result_content = block.get("content", "")
                    if isinstance(result_content, str):
                        size_bytes = len(result_content.encode("utf-8", errors="replace"))
                    elif isinstance(result_content, list):
                        # Multi-block results (e.g., images + text)
                        size_bytes = 0
                        for rb in result_content:
                            if isinstance(rb, dict):
                                text = rb.get("text", "")
                                if text:
                                    size_bytes += len(text.encode("utf-8", errors="replace"))
                                # Image/binary blocks — estimate from base64 if present
                                data = rb.get("data", "")
                                if data:
                                    size_bytes += len(data)
                            elif isinstance(rb, str):
                                size_bytes += len(rb.encode("utf-8", errors="replace"))
                    else:
                        size_bytes = len(json.dumps(result_content).encode("utf-8"))

                    if tool_use_id:
                        tool_result_sizes[tool_use_id] = size_bytes

                # Text blocks — conversation arc (both assistant AND user)
                elif block_type == "text":
                    text = block.get("text", "").strip()
                    if role == "assistant" and text and len(text) > 20:
                        arc.append({
                            "role": "assistant",
                            "text": text[:1000],
                            "timestamp": ts,
                        })

            # After processing all blocks in a list-format user message,
            # collect text blocks into the arc
            if role == "user" and isinstance(content, list):
                user_text = ""
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        user_text += block.get("text", "")
                    elif isinstance(block, str):
                        user_text += block
                user_text = user_text.strip()
                if user_text and not _is_injected_user_text(user_text):
                    arc.append({
                        "role": "user",
                        "text": user_text[:2000],
                        "timestamp": ts,
                    })

        # User messages with string content (simple format)
        elif role == "user":
            text = ""
            if isinstance(content, str):
                text = content
            text = text.strip()
            if text and not _is_injected_user_text(text):
                arc.append({
                    "role": "user",
                    "text": text[:2000],
                    "timestamp": ts,
                })

    # --- Post-processing ---

    # Compute duration
    if session["start_time"] and session["end_time"]:
        start = parse_ts(session["start_time"])
        end = parse_ts(session["end_time"])
        if start and end:
            session["duration_seconds"] = round((end - start).total_seconds())
    session["branches_seen"] = sorted(session["branches_seen"])

    # Compute cost
    cost = estimated_cost(tokens_total, transcript_format)

    # Attach result sizes to tool calls
    for call in tool_calls:
        tid = call.get("tool_use_id", "")
        if tid in tool_result_sizes:
            call["result_size_bytes"] = tool_result_sizes[tid]

    # Compute tool result size stats
    result_size_stats = {}
    if tool_result_sizes:
        sizes_by_tool = defaultdict(list)
        for call in tool_calls:
            if "result_size_bytes" in call:
                sizes_by_tool[call["name"]].append(call["result_size_bytes"])

        for tool_name, sizes in sorted(sizes_by_tool.items(), key=lambda x: -sum(x[1])):
            result_size_stats[tool_name] = {
                "count": len(sizes),
                "total_bytes": sum(sizes),
                "avg_bytes": round(sum(sizes) / len(sizes)),
                "max_bytes": max(sizes),
            }

    # Extract agents
    agents = _extract_agents(tool_calls, subagents_dir)

    # Extract skills
    skills = [
        {"name": c.get("skill_name", ""), "args": c.get("skill_args", ""), "timestamp": c.get("timestamp")}
        for c in tool_calls if c["name"] == "Skill"
    ]

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
        "skills": skills,
        "git": {
            "branches": sorted(branches),
            "commits": commits,
            "pr_operations": prs,
        },
        "files": {k: sorted(v) for k, v in files.items()},
        "conversation_arc": arc,
        "tool_result_sizes": result_size_stats,
    }

    if summary_mode:
        result["tools"] = {
            "counts": dict(tool_counts.most_common()),
            "total_calls": total_tool_calls,
        }
    else:
        result["tools"] = {
            "calls": tool_calls,
            "counts": dict(tool_counts.most_common()),
            "total_calls": total_tool_calls,
        }

    return result


def _extract_agents(tool_calls, subagents_dir=None):
    """Extract agent dispatch details and match with subagent JSONL files."""
    agents = []
    for call in tool_calls:
        if call["name"] == "Agent":
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

    if subagents_dir and os.path.isdir(subagents_dir):
        _match_subagent_files(agents, subagents_dir)

    return agents


def _match_subagent_files(agents, subagents_dir):
    """Match subagent JSONL files to dispatches using timestamp proximity."""
    MAX_MATCH_WINDOW_S = 60
    subagent_info = discover_subagents(subagents_dir)

    # Match by timestamp proximity
    matched_dispatches = set()
    matched_subagents = set()

    for sa_idx, sa in enumerate(subagent_info):
        if not sa["start_time"]:
            continue
        best_match = None
        best_delta = None

        for ag_idx, agent in enumerate(agents):
            if ag_idx in matched_dispatches:
                continue
            dispatch_time = parse_ts(agent["timestamp"])
            if not dispatch_time:
                continue
            delta = abs((sa["start_time"] - dispatch_time).total_seconds())
            if delta <= MAX_MATCH_WINDOW_S and (best_delta is None or delta < best_delta):
                best_match = ag_idx
                best_delta = delta

        if best_match is not None:
            agents[best_match]["tokens"] = sa["tokens"]
            agents[best_match]["estimated_cost_usd"] = sa["cost"]
            agents[best_match]["subagent_file"] = sa["file"]
            agents[best_match]["match_delta_s"] = round(best_delta, 1)
            if sa["meta"]:
                agents[best_match]["meta"] = sa["meta"]
            matched_dispatches.add(best_match)
            matched_subagents.add(sa_idx)

    # Report unmatched subagents
    for sa_idx, sa in enumerate(subagent_info):
        if sa_idx not in matched_subagents:
            agents.append({
                "description": f"[unmatched subagent: {sa['file']}]",
                "type": "unknown",
                "model": "unknown",
                "prompt_preview": "",
                "background": False,
                "timestamp": str(sa["start_time"]) if sa["start_time"] else None,
                "tool_use_id": "",
                "tokens": sa["tokens"],
                "estimated_cost_usd": sa["cost"],
                "subagent_file": sa["file"],
                "match_confidence": "unmatched",
                "meta": sa["meta"],
            })


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
