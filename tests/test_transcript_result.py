from pathlib import Path

import pytest

from agent_retro.transcript_result import extract_transcript

FIXTURES = Path(__file__).parent / "fixtures"
EXPECTED_SUBAGENT_COST = 0.0008


def test_typed_entry_point_preserves_full_and_summary_views() -> None:
    full = extract_transcript(FIXTURES / "full_session.jsonl")
    summary = extract_transcript(FIXTURES / "full_session.jsonl", summary=True)

    assert (full["schema_version"], bool(full["tools"]["calls"])) == ("0.1.0", True)
    assert (summary["tools"]["counts"], summary["conversation_arc"]) == (
        full["tools"]["counts"],
        full["conversation_arc"],
    )
    assert "calls" not in summary["tools"]


def test_typed_entry_point_attributes_subagents_when_available(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = extract_transcript(FIXTURES / "full_session.jsonl")
    assert result["agents"][0]["estimated_cost_usd"] is None
    assert "1 agent dispatch(es) have no subagent cost data" in capsys.readouterr().err
    (tmp_path / "agent.jsonl").write_text(
        '{"timestamp":"2026-04-06T09:01:45Z","message":{"role":"assistant",'
        '"usage":{"output_tokens":10}}}',
        encoding="utf-8",
    )
    attributed = extract_transcript(FIXTURES / "full_session.jsonl", subagents_dir=tmp_path)
    assert attributed["agents"][0]["subagent_file"] == "agent.jsonl"
    assert attributed["agents"][0]["estimated_cost_usd"] == EXPECTED_SUBAGENT_COST
