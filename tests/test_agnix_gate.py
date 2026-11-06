"""Contract tests for the deterministic agnix quality gate."""

import subprocess
import sys
from pathlib import Path
from shutil import copytree, ignore_patterns
from unittest.mock import patch

from scripts import check_agent_config
from scripts.run_quality_gate import commands

ROOT = Path(__file__).resolve().parents[1]
QUALITY_GATE = "python scripts/run_quality_gate.py"


def test_gate_runs_strict_codex_validation() -> None:
    """The wrapper must keep local and automated invocation identical."""
    with patch.object(subprocess, "run") as run:
        check_agent_config.main()

    run.assert_called_once()
    command = run.call_args.args[0]
    assert command[:4] == ["agnix", "--strict", "--target", "codex"]
    assert Path(command[4]).name == "agent-retro"
    assert run.call_args.kwargs == {"check": True}


def test_gate_is_independent_of_checkout_basename(tmp_path: Path) -> None:
    checkout = tmp_path / "not-agent-retro"
    copytree(
        ROOT,
        checkout,
        ignore=ignore_patterns(".git", ".venv", "__pycache__"),
    )

    result = subprocess.run(
        [sys.executable, "scripts/check_agent_config.py"],
        cwd=checkout,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_agnix_is_exactly_pinned() -> None:
    """The development environment must resolve one reproducible version."""
    assert '"agnix==0.60.3"' in (ROOT / "pyproject.toml").read_text()
    lock = (ROOT / "uv.lock").read_text()
    assert 'name = "agnix"' in lock
    assert 'version = "0.60.3"' in lock


def test_precommit_and_ci_use_the_local_gate() -> None:
    """Pre-push and CI must call one wrapper containing the agnix gate."""
    assert QUALITY_GATE in (ROOT / ".pre-commit-config.yaml").read_text()
    assert QUALITY_GATE in (ROOT / ".github/workflows/ci.yml").read_text()
    assert commands("uv")[0][-2:] == ("python", "scripts/check_agent_config.py")
