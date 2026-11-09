"""Contract tests for repository agent instructions."""

from pathlib import Path

AGENT_INSTRUCTIONS = (Path(__file__).resolve().parents[1] / "AGENTS.md").read_text()


def test_github_provider_contract() -> None:
    """GitHub work must use the accepted REST provider, not the stale MCP rule."""
    assert "GitHub REST API" in AGENT_INSTRUCTIONS
    assert "`gh api`" in AGENT_INSTRUCTIONS
    assert "GitHub MCP" not in AGENT_INSTRUCTIONS


def test_live_github_state_is_authoritative() -> None:
    """Remote issue and PR state must win over stale local information."""
    assert "live pull request and issue state" in AGENT_INSTRUCTIONS
    assert "authoritative over stale local refs" in AGENT_INSTRUCTIONS


def test_external_mutation_boundaries_are_explicit() -> None:
    """Instructions must preserve separate authorization boundaries."""
    for boundary in ("pushes", "pull request mutations", "merges", "issue mutations"):
        assert boundary in AGENT_INSTRUCTIONS


def test_verification_matches_the_change_type() -> None:
    """The test policy must require independent evidence without artificial red tests."""
    for contract in (
        "Reproducible bug fixes",
        "highest stable observable boundary",
        "Refactors preserve characterization evidence",
        "Documentation, policy, and build configuration",
        "External integrations",
    ):
        assert contract in AGENT_INSTRUCTIONS
