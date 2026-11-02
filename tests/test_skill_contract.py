"""Product contract tests for the distributable skill."""

from pathlib import Path


SKILL = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text()
OPENAI_METADATA = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"


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


def test_openai_metadata_matches_the_skill_contract() -> None:
    """Distributed UI metadata must describe the same Codex-first workflow."""
    metadata = OPENAI_METADATA.read_text()
    assert 'display_name: "Agent Retro"' in metadata
    assert 'short_description: "Review Codex sessions and improve workflows"' in metadata
    assert "$agent-retro" in metadata
    assert "Codex session" in metadata


def test_openai_metadata_has_no_unsupported_dependencies() -> None:
    """The standalone skill must not claim an MCP or product dependency."""
    metadata = OPENAI_METADATA.read_text()
    assert "dependencies:" not in metadata
    assert "policy:" not in metadata
