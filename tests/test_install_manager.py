import subprocess
from pathlib import Path

import pytest

from scripts.install_manager import InstallError, install, uninstall

ROOT = Path(__file__).resolve().parents[1]
INPUT_ERROR = 2


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for relative in (".venv/bin/python", ".venv/bin/agent-retro", "scripts/daily_codex_retro.py"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
    (root / "SKILL.md").write_text("---\nname: agent-retro\ndescription: Test.\n---\n")
    return root


def test_install_is_repeatable_and_uses_canonical_source(tmp_path: Path) -> None:
    root = repository(tmp_path)
    home = tmp_path / "home"
    calls: list[tuple[str, ...]] = []

    install(root, home, lambda command: calls.append(command) or 0)
    install(root, home, lambda command: calls.append(command) or 0)

    assert (home / ".codex/skills/agent-retro").resolve() == root
    assert (home / ".local/bin/agent-retro").resolve() == root / ".venv/bin/agent-retro"
    plist = (home / "Library/LaunchAgents/com.fosghen.agent-retro.plist").read_text()
    assert str(root / ".venv/bin/python") in plist
    assert any("skills-ref" in command[0] for command in calls)


def test_install_rejects_an_unowned_skill_copy(tmp_path: Path) -> None:
    root = repository(tmp_path)
    target = tmp_path / "home/.codex/skills/agent-retro"
    target.mkdir(parents=True)

    with pytest.raises(InstallError, match="unmanaged path"):
        install(root, tmp_path / "home", lambda _command: 0)


def test_uninstall_removes_managed_files_but_preserves_state(tmp_path: Path) -> None:
    root = repository(tmp_path)
    home = tmp_path / "home"
    state = home / ".local/state/agent-retro/proposals.sqlite3"
    state.parent.mkdir(parents=True)
    state.touch()
    install(root, home, lambda _command: 0)

    uninstall(root, home, lambda _command: 0)

    assert not (home / ".codex/skills/agent-retro").exists()
    assert not (home / ".local/bin/agent-retro").exists()
    assert state.exists()


def test_shell_entrypoint_loads_from_any_directory(tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603 -- fixed test entrypoint
        ["/bin/sh", str(ROOT / "scripts/install_launchd.sh"), "invalid"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == INPUT_ERROR
    assert result.stderr == "Usage: manage_install.py {install|uninstall}\n"
