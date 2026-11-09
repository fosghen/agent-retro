"""Controlled failure fixtures for non-Python publication artifacts."""

from pathlib import Path

from scripts.check_package import build_package, install_wheel, smoke_installed_cli
from scripts.check_shell_plist import check_plist, check_shell

ROOT = Path(__file__).resolve().parents[1]


def test_installer_shell_syntax_rejects_a_controlled_error(tmp_path: Path) -> None:
    installer = tmp_path / "install.sh"
    installer.write_text("if then\n", encoding="utf-8")
    assert not check_shell(installer)


def test_installer_shell_syntax_accepts_repository_script() -> None:
    assert check_shell(ROOT / "scripts" / "install_launchd.sh")
    assert check_shell(ROOT / "scripts" / "smoke_macos_install.sh")


def test_macos_ci_owns_only_the_isolated_install_smoke() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "macos-install:" in workflow
    assert "runs-on: macos-14" in workflow
    assert "./scripts/smoke_macos_install.sh" in workflow


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


def test_package_install_rejects_a_controlled_invalid_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "broken-0.0-py3-none-any.whl"
    wheel.write_text("not a wheel", encoding="utf-8")

    assert not install_wheel(wheel, tmp_path / "venv")


def test_installed_cli_smoke_rejects_a_controlled_failure(tmp_path: Path) -> None:
    executable = tmp_path / "venv" / "bin" / "agent-retro"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    executable.chmod(0o755)

    assert not smoke_installed_cli(executable.parent.parent)
