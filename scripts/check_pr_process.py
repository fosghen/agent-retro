"""Validate the pull request's explicit risk and review declaration."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

RISK = re.compile(r"(?m)^Risk: (low|high)$")
REVIEW = re.compile(r"(?m)^Independent review: (not-used|completed)$")
HIGH_RISK_TRIGGERS = (
    "data migration or persisted-schema change",
    "concurrency, locking, or transaction-boundary change",
    "privacy, security, authentication, or authorization change",
    "destructive operation or external side effect",
    "unresolved correctness uncertainty after self-review",
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
    if len(risk_matches) != 1 or len(review_matches) != 1:
        message = "declare exactly one risk and review status"
        raise ProcessDeclarationError(message)
    risk, review = risk_matches[0], review_matches[0]
    triggers = [label for label in HIGH_RISK_TRIGGERS if checked(body, label)]
    if risk == "low" and (review != "not-used" or triggers):
        message = "low-risk PRs must skip independent review and triggers"
        raise ProcessDeclarationError(message)
    if risk == "high" and (review != "completed" or not triggers):
        message = "high-risk PRs require a trigger and completed review"
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
