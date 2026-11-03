"""Report issue-first development state as one compact JSON document."""

from __future__ import annotations

import json
import re
import shutil

# Executables are resolved explicitly and arguments are never shell-evaluated.
import subprocess  # nosec B404
import sys
from collections.abc import Callable

from scripts.check_change_limits import (
    MAX_COMMIT_LINES,
    MAX_COMMITS,
    MAX_PR_LINES,
    ChangeLimitError,
    count_lines,
)

ISSUE_BRANCH = re.compile(r"(?:^|/)issue-([1-9][0-9]*)(?:-|$)")
Query = Callable[..., str]


class WorkflowStatusError(RuntimeError):
    """The current workflow state cannot be read or is invalid."""


def execute(tool: str, *args: str) -> str:
    """Run one fixed-argument read-only query."""
    executable = shutil.which(tool)
    if executable is None:
        message = f"{tool} executable is unavailable"
        raise WorkflowStatusError(message)
    try:
        result = subprocess.run(  # noqa: S603  # nosec B603
            [executable, *args], check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or f"exit {error.returncode}"
        message = f"{tool} query failed: {detail}"
        raise WorkflowStatusError(message) from error
    return result.stdout.strip()


def collect(query: Query = execute) -> dict[str, object]:
    """Collect local budgets and matching live GitHub state."""
    branch = query("git", "branch", "--show-current")
    match = ISSUE_BRANCH.search(branch)
    if match is None:
        message = "current branch must contain issue-N"
        raise WorkflowStatusError(message)
    issue_number = int(match.group(1))
    commits = int(query("git", "rev-list", "--count", "origin/main..HEAD"))
    changed = count_lines(query("git", "diff", "--numstat", "origin/main...HEAD"))
    staged = count_lines(query("git", "diff", "--cached", "--numstat"))
    issue = json.loads(query("gh", "issue", "view", str(issue_number), "--json", "number,state"))
    if issue.get("number") != issue_number:
        message = f"issue #{issue_number} is absent"
        raise WorkflowStatusError(message)
    pull_requests = json.loads(
        query(
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "all",
            "--limit",
            "1",
            "--json",
            "state",
        )
    )
    pr_state = pull_requests[0]["state"] if pull_requests else None
    return {
        "branch": branch,
        "issue": {"number": issue_number, "state": issue["state"]},
        "pr_state": pr_state,
        "commits": commits,
        "changed_lines": changed,
        "remaining": {
            "commit_lines": max(0, MAX_COMMIT_LINES - staged),
            "commits": max(0, MAX_COMMITS - commits),
            "pr_lines": max(0, MAX_PR_LINES - changed),
        },
    }
