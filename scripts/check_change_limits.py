"""Enforce the repository's small-commit and small-PR policy."""

from __future__ import annotations

import argparse
import re
import shutil

# Only the resolved Git executable is invoked; arguments are not shell-evaluated.
import subprocess  # nosec B404
import sys

MAX_COMMIT_LINES = 100
MAX_PR_LINES = 250
MAX_COMMITS = 5
GENERATED_EXCLUSIONS = frozenset({"uv.lock"})
ISSUE_BRANCH = re.compile(r"(?:^|/)issue-[1-9][0-9]*(?:-|$)")


class ChangeLimitError(ValueError):
    """A branch, commit, or PR violates the change policy."""


def count_lines(numstat: str) -> int:
    """Count additions and deletions, rejecting binary changes."""
    total = 0
    for row in numstat.splitlines():
        additions, deletions, _path = row.split("\t", 2)
        if "-" in (additions, deletions):
            message = "binary changes are forbidden"
            raise ChangeLimitError(message)
        if _path in GENERATED_EXCLUSIONS:
            continue
        total += int(additions) + int(deletions)
    return total


def check(branch: str, commits: dict[str, str]) -> None:
    """Validate the branch, PR commit count, and every commit size."""
    if branch in {"main", "master"}:
        message = f"commits on {branch!r} are forbidden"
        raise ChangeLimitError(message)
    if not ISSUE_BRANCH.search(branch):
        message = "development branch must reference an issue as issue-N"
        raise ChangeLimitError(message)
    if len(commits) > MAX_COMMITS:
        message = f"PR has {len(commits)} commits; maximum is {MAX_COMMITS}"
        raise ChangeLimitError(message)
    total_lines = 0
    for commit, numstat in commits.items():
        lines = count_lines(numstat)
        total_lines += lines
        if lines > MAX_COMMIT_LINES:
            message = f"commit {commit} has {lines} changed lines; maximum is {MAX_COMMIT_LINES}"
            raise ChangeLimitError(message)
    if total_lines > MAX_PR_LINES:
        message = f"PR has {total_lines} changed lines; maximum is {MAX_PR_LINES}"
        raise ChangeLimitError(message)


def git(*args: str) -> str:
    """Run Git and return stripped standard output."""
    executable = shutil.which("git")
    if executable is None:
        message = "Git executable is unavailable"
        raise RuntimeError(message)
    result = subprocess.run(  # noqa: S603  # nosec B603
        [executable, *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def main() -> int:
    """Check either the staged commit or a base-to-head range."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--range", nargs=2, metavar=("BASE", "HEAD"))
    parser.add_argument("--branch")
    args = parser.parse_args()
    branch = args.branch or git("branch", "--show-current")
    if args.range:
        hashes = git("rev-list", "--reverse", f"{args.range[0]}..{args.range[1]}").splitlines()
        commits = {item: git("show", "--format=", "--numstat", item) for item in hashes}
    else:
        commits = {"staged": git("diff", "--cached", "--numstat")}
    try:
        check(branch, commits)
    except ChangeLimitError as error:
        print(f"change policy failed: {error}", file=sys.stderr)  # noqa: T201 -- CLI output
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
