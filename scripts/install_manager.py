"""Install Agent Retro from one canonical source checkout."""

from __future__ import annotations

import os
import plistlib
from collections.abc import Callable
from pathlib import Path

from scripts.install_lock import LOCK_PATH, LockError, read, snapshot, write

LABEL = "com.fosghen.agent-retro"
Execute = Callable[[tuple[str, ...]], int]
PROXY_VARIABLES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
    "all_proxy",
)


class InstallError(RuntimeError):
    """The requested installation would replace an unmanaged artifact."""


def _link(target: Path, source: Path) -> None:
    if target.is_symlink() and target.resolve() == source.resolve():
        return
    if target.exists() or target.is_symlink():
        raise InstallError(f"unmanaged path: {target}")  # noqa: EM102, TRY003
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source)


def _unlink(target: Path, source: Path) -> None:
    if target.is_symlink() and target.resolve() == source.resolve():
        target.unlink()
    elif target.exists() or target.is_symlink():
        raise InstallError(f"unmanaged path: {target}")  # noqa: EM102, TRY003


def _domain() -> str:
    return f"gui/{os.getuid()}"


def _environment() -> dict[str, str]:
    environment = {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}
    environment.update((name, value) for name in PROXY_VARIABLES if (value := os.environ.get(name)))
    return environment


def _require_installed(root: Path, home: Path) -> None:
    links = {
        home / ".codex/skills/agent-retro": root,
        home / ".local/bin/agent-retro": root / ".venv/bin/agent-retro",
    }
    if any(
        not target.is_symlink() or target.resolve() != source.resolve()
        for target, source in links.items()
    ):
        raise InstallError("installed links do not match lock source")  # noqa: EM101, TRY003
    plist = home / f"Library/LaunchAgents/{LABEL}.plist"
    expected = [str(root / ".venv/bin/python"), str(root / "scripts/daily_codex_retro.py")]
    try:
        arguments = plistlib.loads(plist.read_bytes()).get("ProgramArguments")
    except (OSError, plistlib.InvalidFileException, ValueError) as error:
        raise InstallError(f"unmanaged path: {plist}") from error  # noqa: EM102, TRY003
    if arguments != expected:
        raise InstallError(f"unmanaged path: {plist}")  # noqa: EM102, TRY003


def _validate(root: Path, execute: Execute) -> None:
    python = root / ".venv/bin/python"
    cli = root / ".venv/bin/agent-retro"
    script = root / "scripts/daily_codex_retro.py"
    for required in (python, cli, script, root / "SKILL.md"):
        if not required.exists():
            raise InstallError(f"missing artifact: {required}")  # noqa: EM102, TRY003
    validator = root / ".venv/bin/skills-ref"
    if execute((str(validator), "validate", str(root))):
        raise InstallError("skill validation failed")  # noqa: EM101, TRY003


def install(root: Path, home: Path, execute: Execute) -> None:
    """Install repeatable links and a LaunchAgent from one source checkout."""
    _validate(root, execute)
    python = root / ".venv/bin/python"
    cli = root / ".venv/bin/agent-retro"
    script = root / "scripts/daily_codex_retro.py"
    _link(home / ".codex/skills/agent-retro", root)
    _link(home / ".local/bin/agent-retro", cli)
    plist = home / f"Library/LaunchAgents/{LABEL}.plist"
    plist.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": LABEL,
        "ProgramArguments": [str(python), str(script)],
        "StartCalendarInterval": {"Hour": 9, "Minute": 0},
        "ProcessType": "Background",
        "EnvironmentVariables": _environment(),
    }
    plist.write_bytes(plistlib.dumps(payload))
    execute(("launchctl", "bootout", f"{_domain()}/{LABEL}"))
    if execute(("launchctl", "bootstrap", _domain(), str(plist))):
        raise InstallError("LaunchAgent bootstrap failed")  # noqa: EM101, TRY003
    write(home, snapshot(root))


def upgrade(root: Path, home: Path, execute: Execute) -> None:
    """Switch a drift-free installation to the checkout selected by the caller."""
    try:
        locked = read(home)
        current = Path(locked["source"])
        observed = snapshot(current)
    except LockError as error:
        raise InstallError(str(error)) from error
    if observed != locked:
        raise InstallError("local drift detected")  # noqa: EM101, TRY003
    _require_installed(current, home)
    _validate(root, execute)
    uninstall(current, home, execute)
    install(root, home, execute)


def uninstall(root: Path, home: Path, execute: Execute) -> None:
    """Remove managed entry points while preserving local application state."""
    _unlink(home / ".codex/skills/agent-retro", root)
    _unlink(home / ".local/bin/agent-retro", root / ".venv/bin/agent-retro")
    plist = home / f"Library/LaunchAgents/{LABEL}.plist"
    if plist.exists():
        payload = plistlib.loads(plist.read_bytes())
        expected = [str(root / ".venv/bin/python"), str(root / "scripts/daily_codex_retro.py")]
        if payload.get("ProgramArguments") != expected:
            raise InstallError(f"unmanaged path: {plist}")  # noqa: EM102, TRY003
        execute(("launchctl", "bootout", f"{_domain()}/{LABEL}"))
        plist.unlink()
    (home / LOCK_PATH).unlink(missing_ok=True)
