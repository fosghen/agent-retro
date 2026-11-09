import subprocess
from pathlib import Path

from scripts.setup_dev import commands, hooks_installed, setup

ROOT = Path(__file__).parents[1]
EXPECTED_CALLS = 10
FAILURE = 9


def result(
    command: tuple[str, ...], code: int = 0, stdout: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, code, stdout=stdout, stderr="")


def test_commands_install_locked_environment_hooks_and_smoke_checks() -> None:
    planned = commands("/bin/uv")
    assert planned[0] == ("/bin/uv", "sync", "--locked", "--all-groups")
    assert planned[1][-4:] == ("--hook-type", "pre-commit", "--hook-type", "pre-push")
    assert planned[2][-2:] == ("python", "scripts/check_agent_config.py")
    assert planned[3][-2:] == ("agent-retro", "--help")


def test_readme_exposes_one_setup_and_one_gate_command() -> None:
    readme = (ROOT / "README.md").read_text()
    assert "python3 scripts/setup_dev.py" in readme
    assert "uv run --frozen --no-sync python scripts/run_quality_gate.py" in readme


def test_hook_verification_requires_both_executable_hooks(tmp_path: Path) -> None:
    for name in ("pre-commit", "pre-push"):
        hook = tmp_path / name
        hook.touch()
        hook.chmod(0o755)
    assert hooks_installed(tmp_path)
    (tmp_path / "pre-push").chmod(0o644)
    assert not hooks_installed(tmp_path)


def test_setup_is_repeatable_and_stops_on_failure(tmp_path: Path) -> None:
    hooks = tmp_path / ".git/hooks"
    hooks.mkdir(parents=True)
    for name in ("pre-commit", "pre-push"):
        (hooks / name).touch(mode=0o755)

    calls: list[tuple[str, ...]] = []

    def execute(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        stdout = ".git\n" if command[:2] == ("git", "rev-parse") else ""
        return result(command, stdout=stdout)

    assert setup(tmp_path, "/bin/uv", execute) == 0
    assert setup(tmp_path, "/bin/uv", execute) == 0
    assert len(calls) == EXPECTED_CALLS

    assert setup(tmp_path, "/bin/uv", lambda command: result(command, FAILURE)) == FAILURE
