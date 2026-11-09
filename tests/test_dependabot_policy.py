"""Contract for bounded dependency update proposals."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".github/dependabot.yml"
ECOSYSTEMS = 2


def test_dependabot_owns_uv_and_action_updates() -> None:
    text = CONFIG.read_text()

    assert re.findall(r'package-ecosystem: "([^"]+)"', text) == ["uv", "github-actions"]
    assert text.count('interval: "weekly"') == ECOSYSTEMS
    assert text.count("open-pull-requests-limit:") == ECOSYSTEMS
    assert "auto-merge" not in text.lower()


def test_update_noise_is_bounded_and_reviewable() -> None:
    text = CONFIG.read_text()

    assert "open-pull-requests-limit: 2" in text
    assert "open-pull-requests-limit: 1" in text
    assert 'prefix: "chore(deps)"' in text
    assert "dependencies:" in text


def test_security_response_is_documented_separately() -> None:
    policy = (ROOT / "docs/QUALITY.md").read_text()

    assert "Emergency dependency updates" in policy
    assert "do not wait for the weekly cadence" in policy
    assert "never auto-merged" in policy
