"""Run the repository's complete publication gate once, in a stable order."""

from __future__ import annotations

import shutil

# Commands are fixed tuples and are never shell-evaluated.
import subprocess  # nosec B404


def commands(uv: str) -> tuple[tuple[str, ...], ...]:
    """Return the single authoritative full-gate command sequence."""
    prefix = (uv, "run", "--frozen", "--no-sync")
    return (
        (*prefix, "python", "scripts/check_shell_plist.py"),
        (*prefix, "python", "scripts/check_package.py"),
        (*prefix, "python", "scripts/check_agent_config.py"),
        (*prefix, "python", "scripts/check_ruff.py"),
        (*prefix, "pytest"),
        (*prefix, "mypy", "--strict", "src/agent_retro", "scripts"),
        (*prefix, "bandit", "-q", "-r", "src", "scripts"),
        (*prefix, "pip-audit"),
        (*prefix, "agent-retro", "--help"),
    )


def main() -> int:
    """Run every full-gate command, stopping at the first failure."""
    uv = shutil.which("uv")
    if uv is None:
        return 127
    for command in commands(uv):
        result = subprocess.run(command, check=False)  # noqa: S603  # nosec B603
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
