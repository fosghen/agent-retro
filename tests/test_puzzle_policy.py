"""Tests for the issue-backed puzzle marker policy."""

from pathlib import Path

from scripts.puzzle_policy import validate_text

OPEN_ISSUE = 123


def test_rejects_bare_marker_with_actionable_location() -> None:
    errors = validate_text("# TODO later\n", Path("module.py"), lambda _number: True)

    assert len(errors) == 1
    assert "module.py:1" in errors[0]
    assert "TODO(#123, estimate:2h): explanation" in errors[0]


def test_accepts_documented_marker_for_open_issue() -> None:
    marker = f"# TODO(#{OPEN_ISSUE}, estimate:2h): explain deferred parser work"

    assert validate_text(marker, Path("module.py"), lambda number: number == OPEN_ISSUE) == ()
