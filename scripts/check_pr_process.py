"""Validate the pull request's explicit risk and review declaration."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

RISK = re.compile(r"(?m)^Risk: (low|high)$")
REVIEW = re.compile(r"(?m)^Independent review: (not-used|completed)$")
PROVIDER = re.compile(r"(?m)^Review provider: (none|human|model)$")
MODEL_USAGE = re.compile(r"(?m)^Model review usage: (.+)$")
EXTERNAL_EFFECTS = re.compile(
    r"(?m)^External effects: (none|reversible-administration|"
    r"destructive-or-product-facing)$",
)
EXACT_MODEL_USAGE = re.compile(
    r"(?:unavailable|tokens=[0-9]+; cost=(?:unavailable|USD [0-9]+(?:\.[0-9]+)?))",
)
HIGH_RISK_TRIGGERS = (
    "data migration or persisted-schema change",
    "concurrency, locking, or transaction-boundary change",
    "privacy, security, authentication, or authorization change",
    "destructive operation or external side effect",
    "unresolved correctness uncertainty after self-review",
    "explicit user request for independent review",
)
ISSUE_BRANCH = re.compile(r"(?:^|/)issue-([1-9][0-9]*)(?:-|$)")


class ProcessDeclarationError(ValueError):
    """The PR declaration is absent, contradictory, or incomplete."""


def checked(body: str, label: str) -> bool:
    """Return whether one exact Markdown checkbox is checked."""
    return f"- [x] {label}" in body.lower()


def check(body: str, branch: str) -> None:
    """Enforce review only for an explicitly declared high-risk trigger."""
    issue = ISSUE_BRANCH.search(branch)
    if issue is None or not re.search(rf"(?mi)^Closes #{issue.group(1)}$", body):
        message = "branch issue must match an exact Closes #N line"
        raise ProcessDeclarationError(message)
    risk_matches = RISK.findall(body)
    review_matches = REVIEW.findall(body)
    provider_matches = PROVIDER.findall(body)
    usage_matches = MODEL_USAGE.findall(body)
    effect_matches = EXTERNAL_EFFECTS.findall(body)
    declarations = (risk_matches, review_matches, provider_matches, usage_matches, effect_matches)
    if any(len(matches) != 1 for matches in declarations):
        message = "declare exactly one risk, review, provider, usage, and external effect"
        raise ProcessDeclarationError(message)
    risk, review = risk_matches[0], review_matches[0]
    provider, usage, effects = provider_matches[0], usage_matches[0], effect_matches[0]
    triggers = [label for label in HIGH_RISK_TRIGGERS if checked(body, label)]
    if risk == "low" and (review != "not-used" or provider != "none" or triggers):
        message = "low-risk PRs must skip independent review and triggers"
        raise ProcessDeclarationError(message)
    if risk == "high" and (review != "completed" or provider == "none" or not triggers):
        message = "high-risk PRs require a trigger and completed review"
        raise ProcessDeclarationError(message)
    if provider == "model" and EXACT_MODEL_USAGE.fullmatch(usage) is None:
        message = "model review usage must be exact or unavailable"
        raise ProcessDeclarationError(message)
    if provider != "model" and usage != "not-applicable":
        message = "model review usage applies only to model review"
        raise ProcessDeclarationError(message)
    if effects == "destructive-or-product-facing" and risk != "high":
        message = "destructive external effects require high risk"
        raise ProcessDeclarationError(message)


def inputs(argv: list[str] | None) -> tuple[str, str]:
    """Read either an explicit local preflight or the CI environment."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--body-file", type=Path)
    parser.add_argument("--branch")
    args = parser.parse_args(argv)
    if args.body_file is None and args.branch is None:
        return os.environ.get("PR_BODY", ""), os.environ.get("PR_BRANCH", "")
    if args.body_file is None or args.branch is None:
        parser.error("--body-file and --branch must be provided together")
    return args.body_file.read_text(), args.branch


def main(argv: list[str] | None = None) -> int:
    """Validate an explicit draft or the PR body supplied by CI."""
    body, branch = inputs(argv)
    try:
        check(body, branch)
    except ProcessDeclarationError as error:
        print(f"PR process policy failed: {error}", file=sys.stderr)  # noqa: T201
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
