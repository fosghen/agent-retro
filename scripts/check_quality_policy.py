"""Reject drift between the documented quality inventory and its entrypoints."""

from __future__ import annotations

import re
import tomllib
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

from scripts.run_quality_gate import commands

ROOT = Path(__file__).parents[1]
BLOCK = re.compile(r"(?s)<!-- quality-inventory\n(.*?)\n-->")
HOOK = re.compile(r"(?ms)^      - id: ([^\n]+)\n(.*?)(?=^      - id:|\Z)")
CI_STEP = re.compile(r"(?ms)^      - name: ([^\n]+)\n(.*?)(?=^      - (?:name|uses):|\Z)")


class QualityPolicyError(ValueError):
    """The checked inventory disagrees with repository configuration."""


def inventory(document: str) -> dict[str, object]:
    """Parse the single TOML inventory embedded in the quality policy."""
    matches = BLOCK.findall(document)
    if len(matches) != 1:
        message = "quality policy must contain exactly one inventory"
        raise QualityPolicyError(message)
    return tomllib.loads(matches[0])


def check(document: str, hook_config: str, ci_config: str, *, today: date | None = None) -> None:
    """Compare documented tier ownership with local executable entrypoints."""
    policy = inventory(document)
    hooks = dict(HOOK.findall(hook_config))
    pre_push = {name for name, body in hooks.items() if "stages: [pre-push]" in body}
    staged = set(hooks) - pre_push
    if staged != set(cast("list[str]", policy["staged_hooks"])):
        message = "documented staged hooks are stale"
        raise QualityPolicyError(message)
    if pre_push != set(cast("list[str]", policy["pre_push_hooks"])):
        message = "documented pre-push hooks are stale"
        raise QualityPolicyError(message)

    steps = dict(CI_STEP.findall(ci_config))
    expected_steps = dict(item.split("|", 1) for item in cast("list[str]", policy["ci_steps"]))
    if set(steps) != set(expected_steps) or any(
        command not in steps[name] for name, command in expected_steps.items()
    ):
        message = "documented CI entrypoints are stale"
        raise QualityPolicyError(message)

    actual_gate = [" ".join(command[4:]) for command in commands("uv")]
    if actual_gate != cast("list[str]", policy["full_gate"]):
        message = "documented full-gate commands are stale"
        raise QualityPolicyError(message)
    if policy.get("live_facts") != "offline-audit-only":
        message = "live facts must remain outside the offline gate"
        raise QualityPolicyError(message)
    current = today or datetime.now(tz=UTC).date()
    suppressions = cast("list[dict[str, str]]", policy.get("temporary_suppressions", []))
    for suppression in suppressions:
        identity = suppression.get("id", "unnamed")
        if not suppression.get("scope") or not suppression.get("reason"):
            message = f"temporary suppression {identity} requires scope and reason"
            raise QualityPolicyError(message)
        try:
            review = date.fromisoformat(suppression["review_by"])
        except (KeyError, ValueError) as error:
            message = f"temporary suppression {identity} has invalid review date"
            raise QualityPolicyError(message) from error
        if review < current:
            message = f"temporary suppression {identity} expired on {review.isoformat()}"
            raise QualityPolicyError(message)


def main() -> int:
    """Validate the repository-owned files without network access."""
    check(
        (ROOT / "docs/QUALITY.md").read_text(),
        (ROOT / ".pre-commit-config.yaml").read_text(),
        (ROOT / ".github/workflows/ci.yml").read_text(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
