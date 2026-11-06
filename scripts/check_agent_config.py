"""Run the pinned, offline agent-configuration quality gate."""

import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "agent-retro"
IGNORED = shutil.ignore_patterns(
    ".coverage",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "*.pyc",
)


def main() -> None:
    """Validate repository agent configuration for Codex."""
    # The executable and every argument are fixed repository policy.
    with tempfile.TemporaryDirectory(prefix="agent-retro-agnix-") as temp_dir:
        skill_root = Path(temp_dir) / SKILL_NAME
        shutil.copytree(ROOT, skill_root, ignore=IGNORED)
        command = ["agnix", "--strict", "--target", "codex", str(skill_root)]
        subprocess.run(command, check=True)  # noqa: S603  # nosec B603


if __name__ == "__main__":
    main()
