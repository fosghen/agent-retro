"""Supported install and uninstall entry point."""

from __future__ import annotations

import subprocess  # nosec B404
import sys
from pathlib import Path

from scripts.install_manager import install, uninstall, upgrade
from scripts.install_status import inspect


def query(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    """Run one fixed status query and retain its bounded output."""
    return subprocess.run(  # noqa: S603  # nosec B603
        command, check=False, capture_output=True, text=True
    )


def execute(command: tuple[str, ...]) -> int:
    """Run one fixed installation command without a shell."""
    return query(command).returncode


def main(arguments: list[str]) -> int:
    """Dispatch one explicit lifecycle action."""
    actions = {"install": install, "uninstall": uninstall, "upgrade": upgrade}
    if len(arguments) != 1 or arguments[0] not in {*actions, "status"}:
        sys.stderr.write("Usage: manage_install.py {install|status|uninstall|upgrade}\n")
        return 2
    root = Path(__file__).resolve().parents[1]
    if arguments[0] == "status":
        sys.stdout.write("\n".join(inspect(root, Path.home(), query)) + "\n")
        return 0
    actions[arguments[0]](root, Path.home(), execute)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
