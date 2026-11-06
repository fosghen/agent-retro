from pathlib import Path

import pytest
from scripts.install_manager import InstallError, install


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
