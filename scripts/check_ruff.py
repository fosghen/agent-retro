"""Run Ruff across the complete maintained Python scope."""

from __future__ import annotations

import shutil

# Commands are fixed tuples and are never shell-evaluated.
import subprocess  # nosec B404

SCOPE = ("src", "scripts", "tests")


def commands(ruff: str) -> tuple[tuple[str, ...], ...]:
    """Return the shared deterministic Ruff command sequence."""
    return (
        (ruff, "format", "--check", *SCOPE),
        (ruff, "check", *SCOPE),
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
