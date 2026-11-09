"""Reject unowned or unbounded executable-code puzzle markers."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

from scripts.puzzle_policy import validate_text

SCOPES = {
    "src": frozenset({".py"}),
    "scripts": frozenset({".py", ".sh"}),
    "tests": frozenset({".py"}),
    ".github/workflows": frozenset({".yml", ".yaml"}),
    "launchd": frozenset({".plist"}),
}
IssueCheck = Callable[[int], bool]


def maintained_files(root: Path) -> Iterator[Path]:
    """Yield maintained executable files while excluding docs and generated data."""
    for directory, suffixes in SCOPES.items():
        for path in sorted((root / directory).rglob("*")):
            if path.is_file() and path.suffix in suffixes:
                yield path


def check(root: Path, issue_is_open: IssueCheck) -> tuple[str, ...]:
    """Return all puzzle-policy violations under the maintained scopes."""
    errors: list[str] = []
    for path in maintained_files(root):
        errors.extend(validate_text(path.read_text(), path.relative_to(root), issue_is_open))
    return tuple(errors)


def github_issue_is_open(number: int) -> bool:
    """Read one issue state through the authenticated GitHub CLI."""
    gh = shutil.which("gh")
    if gh is None:
        message = "gh executable is unavailable"
        raise RuntimeError(message)
    result = subprocess.run(  # noqa: S603  # nosec B603
        [gh, "issue", "view", str(number), "--json", "state", "--jq", ".state"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"issue #{number} query failed")
    return result.stdout.strip() == "OPEN"


def main() -> int:
    """Check the current repository and print every actionable violation."""
    try:
        errors = check(Path.cwd(), github_issue_is_open)
    except (OSError, RuntimeError, UnicodeError) as error:
        print(f"puzzle policy failed: {error}", file=sys.stderr)  # noqa: T201
        return 1
    for error in errors:
        print(error, file=sys.stderr)  # noqa: T201
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
