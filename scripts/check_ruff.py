"""Run Ruff on the maintained Python scope without legacy extractor debt."""

from __future__ import annotations

import shutil

# Commands are fixed tuples and are never shell-evaluated.
import subprocess  # nosec B404

SCOPE = ("src", "scripts", "tests")
LEGACY_EXCLUDES = "scripts/extract.py,tests/test_extract.py,tests/test_council_fixes.py"


def commands(ruff: str) -> tuple[tuple[str, ...], ...]:
    """Return the shared deterministic Ruff command sequence."""
    suffix = (*SCOPE, "--exclude", LEGACY_EXCLUDES)
    return (
        (ruff, "format", "--check", *suffix),
        (ruff, "check", *suffix),
    )


def main() -> int:
    """Run format and lint checks, stopping on the first violation."""
    ruff = shutil.which("ruff")
    if ruff is None:
        return 127
    for command in commands(ruff):
        result = subprocess.run(command, check=False)  # noqa: S603  # nosec B603
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
