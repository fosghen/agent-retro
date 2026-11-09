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
