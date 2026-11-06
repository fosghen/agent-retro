"""Require a publication branch to reference one open GitHub issue."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess  # nosec B404
import sys

ISSUE_BRANCH = re.compile(r"(?:^|/)issue-([1-9][0-9]*)(?:-|$)")


class IssueStateError(ValueError):
    """The referenced issue is absent or unavailable for development."""


def check(number: int, payload: str) -> None:
    """Validate one live issue response."""
    issue = json.loads(payload)
    if issue.get("number") != number:
        message = f"issue #{number} is absent"
        raise IssueStateError(message)
    if issue.get("state") != "OPEN":
        message = f"issue #{number} must be open"
        raise IssueStateError(message)


def issue_number(branch: str) -> int:
    """Extract the issue identifier from a development branch."""
    match = ISSUE_BRANCH.search(branch)
    if match is None:
        message = "branch must contain issue-N"
        raise IssueStateError(message)
    return int(match.group(1))


def query(number: int) -> str:
    """Read issue state through the authenticated GitHub CLI."""
    executable = shutil.which("gh")
    if executable is None:
        message = "gh executable is unavailable"
        raise IssueStateError(message)
    return subprocess.check_output(  # noqa: S603  # nosec B603
        [executable, "issue", "view", str(number), "--json", "number,state"], text=True
    )


def main() -> int:
    """Validate the branch named by CI."""
    try:
        number = issue_number(os.environ.get("HEAD_BRANCH", ""))
        check(number, query(number))
    except (IssueStateError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"issue state failed: {error}", file=sys.stderr)  # noqa: T201
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
