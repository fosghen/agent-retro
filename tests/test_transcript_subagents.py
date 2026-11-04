import json
from datetime import UTC, datetime
from pathlib import Path

import agent_retro.transcript_subagents as subagent_module
from agent_retro.transcript_aggregate import empty_token_totals


def _write_subagent(path: Path, timestamp: str, input_tokens: int) -> None:
    record = {
        "timestamp": timestamp,
        "message": {
            "role": "assistant",
            "usage": {"input_tokens": input_tokens, "output_tokens": 2},
            "content": [],
        },
    }
    path.write_text(f"{json.dumps(record)}\n", encoding="utf-8")


def test_discovery_loads_sorted_accounting_and_optional_metadata(tmp_path: Path) -> None:
    _write_subagent(tmp_path / "b.jsonl", "2026-11-04T10:00:02Z", 5)
    _write_subagent(tmp_path / "a.jsonl", "2026-11-04T10:00:01Z", 7)
    (tmp_path / "a.meta.json").write_text('{"label":"alpha"}', encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("ignored", encoding="utf-8")

    loaded = subagent_module.discover_subagents(tmp_path)

    expected_input, expected_output = 7, 2
    assert [item["file"] for item in loaded] == ["a.jsonl", "b.jsonl"]
    assert loaded[0]["tokens"]["input_tokens"] == expected_input
    assert loaded[0]["tokens"]["output_tokens"] == expected_output
    assert loaded[0]["cost"] > 0
    assert loaded[0]["start_time"] is not None
    assert loaded[0]["meta"] == {"label": "alpha"}
    assert loaded[1]["meta"] is None


def test_projection_matches_once_and_reports_unmatched() -> None:
    agents = subagent_module.project_agents(
        [{"name": "Agent", "agent_description": "scan", "timestamp": "2026-11-04T10:00:00Z"}]
    )
    tokens = empty_token_totals()
    start = datetime(2026, 11, 4, 10, 0, 5, tzinfo=UTC)
    matched = subagent_module.SubagentInfo(
        file="a.jsonl", tokens=tokens, cost=1.2, start_time=start, meta={"x": 1}
    )
    unmatched = subagent_module.SubagentInfo(
        file="b.jsonl", tokens=tokens, cost=2.3, start_time=None, meta=None
    )

    subagent_module.match_subagents(agents, [matched, unmatched])

    assert agents[0]["subagent_file"] == "a.jsonl"
    assert agents[1]["match_confidence"] == "unmatched"
