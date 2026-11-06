"""Install Agent Retro from one canonical source checkout."""

from __future__ import annotations

import plistlib
from collections.abc import Callable
from pathlib import Path  # noqa: TC003 -- runtime path construction is intentionally local

LABEL = "com.fosghen.agent-retro"
Execute = Callable[[tuple[str, ...]], int]


class InstallError(RuntimeError):
    """The requested installation would replace an unmanaged artifact."""


def _link(target: Path, source: Path) -> None:
    if target.is_symlink() and target.resolve() == source.resolve():
        return
    if target.exists() or target.is_symlink():
        raise InstallError(f"unmanaged path: {target}")  # noqa: EM102, TRY003
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source)


def install(root: Path, home: Path, execute: Execute) -> None:
    """Install repeatable links and a LaunchAgent from one source checkout."""
    python = root / ".venv/bin/python"
    cli = root / ".venv/bin/agent-retro"
    script = root / "scripts/daily_codex_retro.py"
    for required in (python, cli, script, root / "SKILL.md"):
        if not required.exists():
            raise InstallError(f"missing artifact: {required}")  # noqa: EM102, TRY003
    validator = root / ".venv/bin/skills-ref"
    if execute((str(validator), "validate", str(root))):
        raise InstallError("skill validation failed")  # noqa: EM101, TRY003
    _link(home / ".codex/skills/agent-retro", root)
    _link(home / ".local/bin/agent-retro", cli)
    plist = home / f"Library/LaunchAgents/{LABEL}.plist"
    plist.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": LABEL,
        "ProgramArguments": [str(python), str(script)],
        "StartCalendarInterval": {"Hour": 9, "Minute": 0},
        "ProcessType": "Background",
    }
    plist.write_bytes(plistlib.dumps(payload))
