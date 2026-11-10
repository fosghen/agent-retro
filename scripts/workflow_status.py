"""Report issue-first development state as one compact JSON document."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil

# Executables are resolved explicitly and arguments are never shell-evaluated.
import subprocess  # nosec B404
import sys
from collections.abc import Callable, Mapping

from scripts.check_change_limits import (
    MAX_COMMIT_LINES,
    MAX_COMMITS,
    MAX_PR_LINES,
    ChangeLimitError,
    check,
    count_lines,
)
from scripts.check_issue_state import IssueStateError
from scripts.check_issue_state import check as check_issue_state

ISSUE_BRANCH = re.compile(r"(?:^|/)issue-([1-9][0-9]*)(?:-|$)")
Query = Callable[..., str]


class WorkflowStatusError(RuntimeError):
    """The current workflow state cannot be read or is invalid."""


def delivery_repository(query: Query, environ: Mapping[str, str] = os.environ) -> str:
    """Resolve the explicit override or writable origin GitHub repository."""
    if override := environ.get("GH_REPO"):
        return override
    remote = query("git", "remote", "get-url", "--push", "origin")
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+)$", remote)
    if match is None:
        message = "origin push URL must identify a GitHub repository"
        raise WorkflowStatusError(message)
    return f"{match.group(1)}/{match.group(2).removesuffix('.git')}"


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


def require_publication_ready(branch: str, query: Query = execute) -> None:
    """Reject work that cannot be published as one policy-compliant branch."""
    if query("git", "status", "--porcelain"):
        message = "publication requires a clean worktree"
        raise WorkflowStatusError(message)
    hashes = query("git", "rev-list", "--reverse", "origin/main..HEAD").splitlines()
    if not hashes:
        message = "publication requires at least one commit"
        raise WorkflowStatusError(message)
    commits = {item: query("git", "show", "--format=", "--numstat", item) for item in hashes}
    try:
        check(branch, commits)
    except ChangeLimitError as error:
        raise WorkflowStatusError(str(error)) from error


def collect(query: Query = execute, *, publication: bool = False) -> dict[str, object]:
    """Collect local budgets and matching live GitHub state."""
    branch = query("git", "branch", "--show-current")
    match = ISSUE_BRANCH.search(branch)
    if match is None:
        message = "current branch must contain issue-N"
        raise WorkflowStatusError(message)
    if publication:
        require_publication_ready(branch, query)
    issue_number = int(match.group(1))
    repository = delivery_repository(query)
    commits = int(query("git", "rev-list", "--count", "origin/main..HEAD"))
    changed = count_lines(query("git", "diff", "--numstat", "origin/main...HEAD"))
    staged = count_lines(query("git", "diff", "--cached", "--numstat"))
    issue = json.loads(
        query(
            "gh",
            "issue",
            "view",
            str(issue_number),
            "--json",
            "number,state",
            "--repo",
            repository,
        )
    )
    try:
        check_issue_state(issue_number, json.dumps(issue))
    except IssueStateError as error:
        raise WorkflowStatusError(str(error)) from error
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
            "--repo",
            repository,
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


def encode(status: dict[str, object]) -> str:
    """Serialize status without presentation whitespace."""
    return json.dumps(status, separators=(",", ":"), sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    """Print compact status or one actionable error."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--publication", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(encode(collect(publication=args.publication)))  # noqa: T201 -- CLI output
    except (ChangeLimitError, ValueError, WorkflowStatusError) as error:
        print(f"workflow status failed: {error}", file=sys.stderr)  # noqa: T201
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
