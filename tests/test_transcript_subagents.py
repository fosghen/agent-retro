import json
from pathlib import Path

from agent_retro.transcript_subagents import discover_subagents


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

    loaded = discover_subagents(tmp_path)

    expected_input, expected_output = 7, 2
    assert [item["file"] for item in loaded] == ["a.jsonl", "b.jsonl"]
    assert loaded[0]["tokens"]["input_tokens"] == expected_input
    assert loaded[0]["tokens"]["output_tokens"] == expected_output
    assert loaded[0]["cost"] > 0
    assert loaded[0]["start_time"] is not None
    assert loaded[0]["meta"] == {"label": "alpha"}
    assert loaded[1]["meta"] is None
