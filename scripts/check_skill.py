"""Validate the distributable skill with the Agent Skills reference CLI."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_skill(path: Path) -> bool:
    """Return whether skills-ref accepts the supplied skill directory."""
    validator = shutil.which("skills-ref")
    if validator is None:
        return False
    result = subprocess.run(  # noqa: S603  # nosec B603: fixed reference-validator command
        [validator, "validate", str(path)], check=False
    )
    return result.returncode == 0


def main() -> int:
    """Validate the repository skill against the official reference tool."""
    return 0 if validate_skill(ROOT) else 1


if __name__ == "__main__":
    raise SystemExit(main())
