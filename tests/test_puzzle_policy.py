"""Tests for the issue-backed puzzle marker policy."""

from pathlib import Path

from scripts.check_puzzles import check
from scripts.puzzle_policy import validate_text

OPEN_ISSUE = 123
TOKEN = "TO" + "DO"


def test_rejects_bare_marker_with_actionable_location() -> None:
    errors = validate_text(f"# {TOKEN} later\n", Path("module.py"), lambda _number: True)

    assert len(errors) == 1
    assert "module.py:1" in errors[0]
    assert f"{TOKEN}(#123, estimate:2h): explanation" in errors[0]


def test_accepts_documented_marker_for_open_issue() -> None:
    marker = f"# {TOKEN}(#{OPEN_ISSUE}, estimate:2h): explain deferred parser work"

    assert validate_text(marker, Path("module.py"), lambda number: number == OPEN_ISSUE) == ()


def test_scans_only_maintained_executable_scope(tmp_path: Path) -> None:
    (source := tmp_path / "src").mkdir()
    (source / "bare.py").write_text(f"# {TOKEN}: missing owner")
    errors = check(tmp_path, lambda _number: True)
    assert len(errors) == 1
    assert "src/bare.py:1" in errors[0]
