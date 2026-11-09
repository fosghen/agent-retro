"""Inspect the read-only health of an Agent Retro installation."""

from __future__ import annotations

import re

# CompletedProcess is type-only; this module never executes a command.
import subprocess  # nosec B404
from collections.abc import Callable
from importlib.metadata import version
from typing import TYPE_CHECKING

from scripts.install_health import launchagent_status, lock_status

if TYPE_CHECKING:
    from pathlib import Path

Query = Callable[[tuple[str, ...]], subprocess.CompletedProcess[str]]
SKILL_VERSION = re.compile(r'(?m)^  version: "([^"]+)"$')
SOURCE_VERSION = version("agent-retro")


def _skill_version(path: Path) -> str | None:
    match = SKILL_VERSION.search(path.read_text()) if path.is_file() else None
    return match.group(1) if match else None


def _cli(root: Path, home: Path, query: Query) -> str:
    path, expected = home / ".local/bin/agent-retro", root / ".venv/bin/agent-retro"
    if not path.exists():
        return "cli: missing; run install"
    if not path.is_symlink() or path.resolve() != expected.resolve():
        return "cli: mismatch path; reinstall"
    result = query((str(path), "--version"))
    installed = result.stdout.strip() if result.returncode == 0 else "unavailable"
    if installed != SOURCE_VERSION:
        return f"cli: mismatch installed={installed} source={SOURCE_VERSION}; reinstall"
    return f"cli: ok version={installed}"


def _skill(root: Path, home: Path) -> str:
    path = home / ".codex/skills/agent-retro"
    if not path.exists():
        return "skill: missing; run install"
    if not path.is_symlink() or path.resolve() != root.resolve():
        return "skill: mismatch path is not canonical source; reinstall"
    installed = _skill_version(path / "SKILL.md") or "unavailable"
    source = _skill_version(root / "SKILL.md") or "unavailable"
    if installed != source:
        return f"skill: mismatch installed={installed} source={source}; reinstall"
    return f"skill: ok version={installed}"


def inspect(root: Path, home: Path, query: Query) -> tuple[str, ...]:
    """Return actionable component status without mutating the installation."""
    return (
        f"source: ok version={SOURCE_VERSION}",
        _cli(root, home, query),
        _skill(root, home),
        lock_status(home),
        launchagent_status(root, home, query),
    )
