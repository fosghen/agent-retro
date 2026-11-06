"""Acceptance tests for the Agent Skills reference validator gate."""

import subprocess
import sys
from pathlib import Path

from scripts.check_skill import validate_skill

ROOT = Path(__file__).resolve().parents[1]


def test_official_validator_rejects_invalid_skill(tmp_path: Path) -> None:
    skill = tmp_path / "broken-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("missing frontmatter\n", encoding="utf-8")

    assert not validate_skill(skill)


def test_official_validator_accepts_repository_skill() -> None:
    assert validate_skill(ROOT)


def test_reference_validator_is_pinned_in_the_locked_environment() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")

    assert 'rev = "83021e2be457a9b6679148719c1f6074f0ad975e"' in project
    assert 'name = "skills-ref"' in lock
    assert "rev=83021e2be457a9b6679148719c1f6074f0ad975e" in lock


def test_skill_check_runs_the_reference_validator() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_skill.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
