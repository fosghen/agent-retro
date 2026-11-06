"""Build a wheel in a temporary directory to validate package metadata."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_package(root: Path, output: Path) -> bool:
    """Return whether uv produced a wheel for the project."""
    uv = shutil.which("uv")
    if uv is None:
        return False
    result = subprocess.run(  # noqa: S603  # nosec B603: fixed uv build command
        [uv, "build", "--wheel", "--out-dir", str(output)], cwd=root, check=False
    )
    return result.returncode == 0 and any(output.glob("*.whl"))


def install_wheel(wheel: Path, environment: Path) -> bool:
    """Install one built wheel into an isolated, dependency-free environment."""
    uv = shutil.which("uv")
    if uv is None:
        return False
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    venv = subprocess.run(  # noqa: S603  # nosec B603: fixed uv command
        [uv, "venv", "--python", sys.executable, str(environment)], check=False
    )
    if venv.returncode:
        return False
    installed = subprocess.run(  # noqa: S603  # nosec B603: fixed uv command
        [uv, "pip", "install", "--no-deps", "--python", str(python), str(wheel)],
        check=False,
    )
    return installed.returncode == 0


def smoke_installed_cli(environment: Path) -> bool:
    """Run the CLI executable from the isolated environment's scripts directory."""
    scripts = environment / ("Scripts" if sys.platform == "win32" else "bin")
    executable = scripts / ("agent-retro.exe" if sys.platform == "win32" else "agent-retro")
    if not executable.is_file():
        return False
    result = subprocess.run(  # noqa: S603  # nosec B603: exact installed artifact
        [str(executable), "--help"], check=False
    )
    return result.returncode == 0


def main() -> int:
    """Build the project without leaving distribution artifacts in the checkout."""
    with tempfile.TemporaryDirectory(prefix="agent-retro-build-") as directory:
        output = Path(directory)
        if not build_package(ROOT, output):
            return 1
        wheel = next(output.glob("*.whl"), None)
        environment = output / "venv"
        return int(
            wheel is None
            or not install_wheel(wheel, environment)
            or not smoke_installed_cli(environment)
        )


if __name__ == "__main__":
    raise SystemExit(main())
