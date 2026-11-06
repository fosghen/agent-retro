"""Build a wheel in a temporary directory to validate package metadata."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
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


def main() -> int:
    """Build the project without leaving distribution artifacts in the checkout."""
    with tempfile.TemporaryDirectory(prefix="agent-retro-build-") as directory:
        return 0 if build_package(ROOT, Path(directory)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
