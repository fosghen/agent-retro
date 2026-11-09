"""Validate the LaunchAgent installer and rendered plist template."""

import plistlib
import shutil
import subprocess  # nosec B404
from pathlib import Path
from xml.parsers.expat import ExpatError

ROOT = Path(__file__).resolve().parents[1]


def check_shell(installer: Path) -> bool:
    """Return whether the installer parses as POSIX shell."""
    shell = shutil.which("sh")
    if shell is None:
        return False
    return (
        subprocess.run(  # noqa: S603  # nosec B603: fixed shell syntax command
            [shell, "-n", str(installer)], check=False
        ).returncode
        == 0
    )


def check_plist(template: Path) -> bool:
    """Return whether the launchd template renders as a plist."""
    rendered = template.read_text(encoding="utf-8")
    replacements = (
        ("__PYTHON__", "/usr/bin/python3"),
        ("__SCRIPT__", str(Path.cwd() / "daily.py")),
        ("__LOG_DIR__", str(Path.cwd() / "logs")),
    )
    for token, value in replacements:
        rendered = rendered.replace(token, value)
    try:
        return isinstance(plistlib.loads(rendered.encode()), dict)
    except (plistlib.InvalidFileException, ExpatError, ValueError):
        return False


def main() -> int:
    """Run both LaunchAgent artifact checks."""
    scripts = ("install_launchd.sh", "smoke_macos_install.sh")
    if not all(check_shell(ROOT / "scripts" / script) for script in scripts):
        return 1
    return 0 if check_plist(ROOT / "launchd" / "com.fosghen.agent-retro.plist.in") else 1


if __name__ == "__main__":
    raise SystemExit(main())
