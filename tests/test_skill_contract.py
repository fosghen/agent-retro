"""Product contract tests for the distributable skill."""

from pathlib import Path


SKILL = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text()


def test_metadata_describes_the_maintained_runtime() -> None:
    """Metadata must identify this fork and its supported Python runtime."""
    assert "author: fosghen" in SKILL
    assert "Python 3.12" in SKILL
    assert "Python 3.8+" not in SKILL


def test_codex_is_the_primary_session_source() -> None:
    """Codex discovery must precede the explicitly imported Claude format."""
    codex_discovery = SKILL.index("**OpenAI Codex:**")
    claude_import = SKILL.index("**Claude Code import:**")
    assert codex_discovery < claude_import
    assert "Claude Code import" in SKILL


def test_retro_output_uses_the_codex_worklog() -> None:
    """The canonical report belongs under the Codex worklog."""
    assert "~/.codex/worklog/retros/" in SKILL
    assert "~/.claude/worklog/retros/" not in SKILL
