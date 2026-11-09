"""Bootstrap the locked development environment and repository hooks."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).parents[1]
Execute = Callable[[tuple[str, ...]], subprocess.CompletedProcess[str]]


def commands(uv: str) -> tuple[tuple[str, ...], ...]:
    """Return the idempotent dependency, hook, and smoke commands."""
    run = (uv, "run", "--frozen", "--no-sync")
    hooks = ("--hook-type", "pre-commit", "--hook-type", "pre-push")
    return (
        (uv, "sync", "--locked", "--all-groups"),
        (*run, "pre-commit", "install", "--install-hooks", *hooks),
        (*run, "python", "scripts/check_agent_config.py"),
        (*run, "agent-retro", "--help"),
    )


def hooks_installed(directory: Path) -> bool:
    """Return whether both repository hook entrypoints are executable."""
    return all(
        (directory / name).is_file() and os.access(directory / name, os.X_OK)
        for name in ("pre-commit", "pre-push")
    )


def setup(root: Path, uv: str, execute: Execute) -> int:
    """Run setup once and verify the installed hooks before smoke checks."""
    planned = commands(uv)
    for command in planned[:2]:
        if result := execute(command).returncode:
            return result
    git = execute(("git", "rev-parse", "--git-common-dir"))
    if git.returncode:
        return git.returncode
    common = Path(git.stdout.strip())
    hook_directory = (root / common if not common.is_absolute() else common) / "hooks"
    if not hooks_installed(hook_directory):
        return 1
    for command in planned[2:]:
        if result := execute(command).returncode:
            return result
    return 0


def main() -> int:
    """Bootstrap the current checkout with fixed, non-shell commands."""
    uv = shutil.which("uv")
    if uv is None:
        return 127

    def execute(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603  # nosec B603
            command, cwd=ROOT, capture_output=True, text=True, check=False
        )

    return setup(ROOT, uv, execute)


if __name__ == "__main__":
    raise SystemExit(main())
