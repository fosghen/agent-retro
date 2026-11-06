"""Supported install and uninstall entry point."""

from __future__ import annotations

import subprocess  # nosec B404
import sys
from pathlib import Path

from scripts.install_manager import install, uninstall


def execute(command: tuple[str, ...]) -> int:
    """Run one fixed installation command without a shell."""
    return subprocess.run(command, check=False).returncode  # noqa: S603  # nosec B603


def main(arguments: list[str]) -> int:
    """Dispatch one explicit lifecycle action."""
    actions = {"install": install, "uninstall": uninstall}
    if len(arguments) != 1 or arguments[0] not in actions:
        sys.stderr.write("Usage: manage_install.py {install|uninstall}\n")
        return 2
    root = Path(__file__).resolve().parents[1]
    actions[arguments[0]](root, Path.home(), execute)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
