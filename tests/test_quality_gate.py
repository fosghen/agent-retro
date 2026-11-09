import subprocess
import tomllib
import unittest
from pathlib import Path
from unittest.mock import call, patch

from scripts.run_quality_gate import commands, main


class QualityGateTests(unittest.TestCase):
    def test_coverage_policy_preserves_measured_ratchet(self) -> None:
        config = tomllib.loads(Path("pyproject.toml").read_text())
        self.assertIn("--cov-branch", config["tool"]["pytest"]["ini_options"]["addopts"])
        self.assertEqual(config["tool"]["coverage"]["report"]["fail_under"], 85)

    def test_commands_are_complete_and_deterministic(self) -> None:
        result = commands("/bin/uv")
        self.assertEqual(len(result), 11)
        self.assertEqual(result[0][-2:], ("python", "scripts/check_agent_config.py"))
        self.assertEqual(result[1][-2:], ("python", "scripts/check_shell_plist.py"))
        self.assertEqual(result[2][-2:], ("python", "scripts/check_package.py"))
        self.assertEqual(result[3][-2:], ("python", "scripts/check_ruff.py"))
        self.assertEqual(result[4][-2:], ("-m", "scripts.check_puzzles"))
        self.assertEqual(result[5][-1], "pytest")
        self.assertEqual(result[6][-4:], ("mypy", "--strict", "src/agent_retro", "scripts"))
        self.assertEqual(result[-2][-2:], ("agent-retro", "--help"))
        self.assertEqual(result[-1][-2:], ("python", "scripts/check_skill.py"))
        self.assertTrue(all("--frozen" in item and "--no-sync" in item for item in result))

    def test_stops_at_first_failure(self) -> None:
        with (
            patch("scripts.run_quality_gate.shutil.which", return_value="/bin/uv"),
            patch("scripts.run_quality_gate.subprocess.run") as run,
        ):
            run.side_effect = (
                subprocess.CompletedProcess([], 0),
                subprocess.CompletedProcess([], 9),
            )

            self.assertEqual(main(), 9)
            self.assertEqual(run.call_count, 2)
            expected = commands("/bin/uv")
            self.assertEqual(
                run.call_args_list,
                [call(expected[0], check=False), call(expected[1], check=False)],
            )

    def test_missing_uv_is_bounded(self) -> None:
        with patch("scripts.run_quality_gate.shutil.which", return_value=None):
            self.assertEqual(main(), 127)
