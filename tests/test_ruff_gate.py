import subprocess
import unittest
from unittest.mock import call, patch

from scripts.check_ruff import commands, main


class RuffGateTests(unittest.TestCase):
    def test_commands_cover_format_and_lint(self) -> None:
        result = commands("/bin/ruff")
        self.assertEqual(
            result,
            (
                ("/bin/ruff", "format", "--check", "src", "scripts", "tests"),
                ("/bin/ruff", "check", "src", "scripts", "tests"),
            ),
        )

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
