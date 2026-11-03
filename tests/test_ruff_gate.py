import subprocess
import unittest
from unittest.mock import call, patch

from scripts.check_ruff import LEGACY_EXCLUDES, commands, main


class RuffGateTests(unittest.TestCase):
    def test_scope_names_only_legacy_extractor_files(self) -> None:
        self.assertEqual(
            LEGACY_EXCLUDES,
            "scripts/extract.py,tests/test_extract.py,tests/test_council_fixes.py",
        )

    def test_commands_cover_format_and_lint(self) -> None:
        result = commands("/bin/ruff")
        self.assertEqual(result[0][:3], ("/bin/ruff", "format", "--check"))
        self.assertEqual(result[1][:2], ("/bin/ruff", "check"))
        self.assertTrue(all("--exclude" in command for command in result))

    def test_controlled_violation_stops_the_gate(self) -> None:
        with (
            patch("scripts.check_ruff.shutil.which", return_value="/bin/ruff"),
            patch("scripts.check_ruff.subprocess.run") as run,
        ):
            run.return_value = subprocess.CompletedProcess([], 9)
            self.assertEqual(main(), 9)
        run.assert_called_once_with(commands("/bin/ruff")[0], check=False)

    def test_success_runs_both_checks(self) -> None:
        with (
            patch("scripts.check_ruff.shutil.which", return_value="/bin/ruff"),
            patch("scripts.check_ruff.subprocess.run") as run,
        ):
            run.return_value = subprocess.CompletedProcess([], 0)
            self.assertEqual(main(), 0)
        self.assertEqual(
            run.call_args_list,
            [call(command, check=False) for command in commands("/bin/ruff")],
        )

    def test_missing_ruff_is_bounded(self) -> None:
        with patch("scripts.check_ruff.shutil.which", return_value=None):
            self.assertEqual(main(), 127)
