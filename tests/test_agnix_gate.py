"""Contract tests for the deterministic agnix quality gate."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from scripts import check_agent_config


ROOT = Path(__file__).resolve().parents[1]
GATE_COMMAND = "python scripts/check_agent_config.py"


def test_gate_runs_strict_codex_validation() -> None:
    """The wrapper must keep local and automated invocation identical."""
    with patch.object(subprocess, "run") as run:
        check_agent_config.main()

    run.assert_called_once_with(
        ["agnix", "--strict", "--target", "codex", "."],
        check=True,
    )


def test_agnix_is_exactly_pinned() -> None:
    """The development environment must resolve one reproducible version."""
    assert '"agnix==0.60.3"' in (ROOT / "pyproject.toml").read_text()
    lock = (ROOT / "uv.lock").read_text()
    assert 'name = "agnix"' in lock
    assert 'version = "0.60.3"' in lock


def test_precommit_and_ci_use_the_local_gate() -> None:
    """Pre-commit and CI must call the same offline wrapper."""
    assert GATE_COMMAND in (ROOT / ".pre-commit-config.yaml").read_text()
    assert GATE_COMMAND in (ROOT / ".github/workflows/ci.yml").read_text()
