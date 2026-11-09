"""Reject unowned or unbounded executable-code puzzle markers."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from scripts.puzzle_policy import validate_text

if TYPE_CHECKING:
    from pathlib import Path

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
