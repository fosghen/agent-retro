"""Controlled failure fixtures for non-Python publication artifacts."""

from pathlib import Path

from scripts.check_package import build_package
from scripts.check_shell_plist import check_plist, check_shell

ROOT = Path(__file__).resolve().parents[1]


def test_installer_shell_syntax_rejects_a_controlled_error(tmp_path: Path) -> None:
    installer = tmp_path / "install.sh"
    installer.write_text("if then\n", encoding="utf-8")
    assert not check_shell(installer)


def test_installer_shell_syntax_accepts_repository_script() -> None:
    assert check_shell(ROOT / "scripts" / "install_launchd.sh")


def test_plist_parser_rejects_a_controlled_error(tmp_path: Path) -> None:
    template = tmp_path / "broken.plist.in"
    template.write_text("<plist><dict>", encoding="utf-8")
    assert not check_plist(template)


def test_plist_template_renders_as_valid_configuration() -> None:
    template = ROOT / "launchd" / "com.fosghen.agent-retro.plist.in"
    assert check_plist(template)


def test_package_build_rejects_a_controlled_configuration_error(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[invalid\n", encoding="utf-8")
    assert not build_package(project, tmp_path / "dist")
