from datetime import date
from pathlib import Path

import pytest

from scripts.check_quality_policy import QualityPolicyError, check

ROOT = Path(__file__).parents[1]


def repository_inputs() -> tuple[str, str, str]:
    return (
        (ROOT / "docs/QUALITY.md").read_text(),
        (ROOT / ".pre-commit-config.yaml").read_text(),
        (ROOT / ".github/workflows/ci.yml").read_text(),
    )


def test_repository_quality_inventory_matches_entrypoints() -> None:
    check(*repository_inputs())


def test_stale_documented_hook_fails() -> None:
    docs, hooks, ci = repository_inputs()
    stale = docs.replace('"scoped-ruff"', '"stale-ruff"')
    with pytest.raises(QualityPolicyError, match="staged hooks"):
        check(stale, hooks, ci)


def test_missing_ci_command_fails() -> None:
    docs, hooks, ci = repository_inputs()
    missing = ci.replace("python scripts/check_pr_process.py", "true")
    with pytest.raises(QualityPolicyError, match="CI entrypoints"):
        check(docs, hooks, missing)


def test_expired_temporary_suppression_fails_with_identity() -> None:
    docs, hooks, ci = repository_inputs()
    expired = docs.replace(
        "temporary_suppressions = []",
        'temporary_suppressions = [{ id = "legacy", scope = "one.py", '
        'reason = "migration", review_by = "2026-11-08" }]',
    )
    with pytest.raises(QualityPolicyError, match=r"legacy.*2026-11-08"):
        check(expired, hooks, ci, today=date(2026, 11, 9))


def test_incomplete_temporary_suppression_fails() -> None:
    docs, hooks, ci = repository_inputs()
    incomplete = docs.replace(
        "temporary_suppressions = []",
        'temporary_suppressions = [{ id = "broad", review_by = "2026-12-01" }]',
    )
    with pytest.raises(QualityPolicyError, match="scope and reason"):
        check(incomplete, hooks, ci, today=date(2026, 11, 9))
