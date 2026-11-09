import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.install_manager import InstallError, install, uninstall, upgrade

ROOT = Path(__file__).resolve().parents[1]
INPUT_ERROR = 2
REVISION_LENGTH = 40
HASH_LENGTH = 64


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for relative in (".venv/bin/python", ".venv/bin/agent-retro", "scripts/daily_codex_retro.py"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
    (root / "SKILL.md").write_text("---\nname: agent-retro\ndescription: Test.\n---\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # noqa: S603, S607
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)  # noqa: S603, S607
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
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
    lock = json.loads((home / ".local/state/agent-retro/install-lock.json").read_text())
    assert lock["source"] == str(root.resolve())
    assert len(lock["revision"]) == REVISION_LENGTH
    assert len(lock["content_hash"]) == HASH_LENGTH


def test_upgrade_rejects_drift_before_replacing_links(tmp_path: Path) -> None:
    old = repository(tmp_path / "old")
    selected = repository(tmp_path / "selected")
    home = tmp_path / "home"
    install(old, home, lambda _command: 0)
    (old / "SKILL.md").write_text("locally changed")

    with pytest.raises(InstallError, match="local drift"):
        upgrade(selected, home, lambda _command: 0)

    assert (home / ".codex/skills/agent-retro").resolve() == old


def test_upgrade_preflights_all_installed_links(tmp_path: Path) -> None:
    old = repository(tmp_path / "old")
    selected = repository(tmp_path / "selected")
    home = tmp_path / "home"
    install(old, home, lambda _command: 0)
    cli = home / ".local/bin/agent-retro"
    cli.unlink()
    cli.symlink_to(selected / ".venv/bin/agent-retro")

    with pytest.raises(InstallError, match="installed links"):
        upgrade(selected, home, lambda _command: 0)

    assert (home / ".codex/skills/agent-retro").resolve() == old


def test_upgrade_switches_to_selected_checkout_and_refreshes_lock(tmp_path: Path) -> None:
    old = repository(tmp_path / "old")
    selected = repository(tmp_path / "selected")
    home = tmp_path / "home"
    install(old, home, lambda _command: 0)

    upgrade(selected, home, lambda _command: 0)

    lock = json.loads((home / ".local/state/agent-retro/install-lock.json").read_text())
    assert (home / ".codex/skills/agent-retro").resolve() == selected
    assert lock["source"] == str(selected.resolve())


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
    assert result.stderr == "Usage: manage_install.py {install|status|uninstall|upgrade}\n"

    status = subprocess.run(  # noqa: S603 -- fixed supported entrypoint
        ["/bin/sh", str(ROOT / "scripts/install_launchd.sh"), "status"],
        cwd=tmp_path,
        env=os.environ | {"HOME": str(tmp_path / "empty-home")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert status.returncode == 0
    assert "cli: missing; run install" in status.stdout
    assert "launchagent: missing; run install" in status.stdout


def test_readme_uses_supported_install_lifecycle() -> None:
    readme = (ROOT / "README.md").read_text()
    commands = (
        'git clone https://github.com/fosghen/agent-retro.git "$HOME/agent-retro-src"',
        'cd "$HOME/agent-retro-src"',
        "uv sync --locked --all-groups",
        "./scripts/install_launchd.sh install",
        "./scripts/install_launchd.sh upgrade",
        "./scripts/install_launchd.sh uninstall",
    )
    assert all(command in readme for command in commands)
    assert "canonical source" in readme
    assert "unmanaged" in readme
    assert "./scripts/install_launchd.sh status" in readme
    assert "selected release checkout" in readme
