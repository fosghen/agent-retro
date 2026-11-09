import json
import plistlib
import subprocess
from pathlib import Path

from scripts.install_status import inspect


def completed(
    command: tuple[str, ...], code: int = 0, output: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, code, stdout=output, stderr="")


def source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    cli = root / ".venv/bin/agent-retro"
    cli.parent.mkdir(parents=True)
    cli.touch()
    (root / "scripts").mkdir()
    (root / "scripts/daily_codex_retro.py").touch()
    (root / "SKILL.md").write_text('metadata:\n  version: "0.2.0"\n')
    return root


def test_status_reports_versions_lock_and_loaded_schedule(tmp_path: Path) -> None:
    root, home = source(tmp_path), tmp_path / "home"
    skill = home / ".codex/skills/agent-retro"
    cli = home / ".local/bin/agent-retro"
    skill.parent.mkdir(parents=True)
    cli.parent.mkdir(parents=True)
    skill.symlink_to(root)
    cli.symlink_to(root / ".venv/bin/agent-retro")
    lock = home / ".local/state/agent-retro/install-lock.json"
    lock.parent.mkdir(parents=True)
    lock.write_text(json.dumps({"source": "github", "revision": "abc", "content_hash": "123"}))
    plist = home / "Library/LaunchAgents/com.fosghen.agent-retro.plist"
    plist.parent.mkdir(parents=True)
    plist.write_bytes(
        plistlib.dumps(
            {
                "ProgramArguments": [
                    str(root / ".venv/bin/python"),
                    str(root / "scripts/daily_codex_retro.py"),
                ],
                "StartCalendarInterval": {"Hour": 9, "Minute": 0},
            }
        )
    )

    def query(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        return completed(command, output="0.2.0\n" if command[-1] == "--version" else "")

    status = inspect(root, home, query)
    assert status == (
        "source: ok version=0.2.0",
        "cli: ok version=0.2.0",
        "skill: ok version=0.2.0",
        "lock: ok source=github revision=abc hash=123",
        "launchagent: ok schedule=09:00 loaded",
    )


def test_status_reports_missing_components_without_queries(tmp_path: Path) -> None:
    root = source(tmp_path)
    status = inspect(root, tmp_path / "empty", lambda command: completed(command, 99))
    assert status[1:] == (
        "cli: missing; run install",
        "skill: missing; run install",
        "lock: missing; locked upgrade unavailable",
        "launchagent: missing; run install",
    )
