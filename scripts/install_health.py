"""Read lock and LaunchAgent health without mutating installation state."""

from __future__ import annotations

import json
import os
import plistlib
import subprocess
from collections.abc import Callable
from typing import TYPE_CHECKING

from scripts.install_manager import LABEL

if TYPE_CHECKING:
    from pathlib import Path

Query = Callable[[tuple[str, ...]], subprocess.CompletedProcess[str]]


def lock_status(home: Path) -> str:
    """Return the selected revision status from the future-proof lock path."""
    path = home / ".local/state/agent-retro/install-lock.json"
    if not path.is_file():
        return "lock: missing; locked upgrade unavailable"
    try:
        value = json.loads(path.read_text())
        fields = tuple(value[name] for name in ("source", "revision", "content_hash"))
        if not all(isinstance(field, str) and field for field in fields):
            raise ValueError  # noqa: TRY301
    except (OSError, ValueError, KeyError, TypeError):
        return "lock: invalid; run locked upgrade"
    return f"lock: ok source={fields[0]} revision={fields[1]} hash={fields[2]}"


def launchagent_status(root: Path, home: Path, query: Query) -> str:
    """Return schedule and loaded state for the managed LaunchAgent."""
    path = home / f"Library/LaunchAgents/{LABEL}.plist"
    if not path.is_file():
        return "launchagent: missing; run install"
    try:
        value = plistlib.loads(path.read_bytes())
    except (OSError, plistlib.InvalidFileException, ValueError):
        return "launchagent: invalid plist; reinstall"
    expected = [str(root / ".venv/bin/python"), str(root / "scripts/daily_codex_retro.py")]
    if value.get("ProgramArguments") != expected or value.get("StartCalendarInterval") != {
        "Hour": 9,
        "Minute": 0,
    }:
        return "launchagent: mismatch schedule or command; reinstall"
    loaded = query(("launchctl", "print", f"gui/{os.getuid()}/{LABEL}")).returncode == 0
    state = "loaded" if loaded else "not-loaded; run install"
    return f"launchagent: ok schedule=09:00 {state}"
