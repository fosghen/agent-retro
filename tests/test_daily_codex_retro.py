import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from scripts.daily_codex_retro import command, session_dir


class DailyCodexRetroTests(unittest.TestCase):
    def test_session_directory_uses_codex_date_partition(self) -> None:
        path = session_dir(Path("/home/test"), date(2026, 11, 2))
        self.assertEqual(path, Path("/home/test/.codex/sessions/2026/11/02"))

    @patch("scripts.daily_codex_retro.shutil.which", return_value="/bin/codex")
    def test_command_is_read_only_and_writes_requested_report(self, _which) -> None:
        report = Path("/tmp/retro.md")
        result = command(Path("/home/test"), date(2026, 11, 2), report)
        self.assertEqual(result[0:2], ["/bin/codex", "exec"])
        self.assertIn("read-only", result)
        self.assertIn(str(report), result)
        self.assertIn("2026/11/02", result[-1])
        self.assertIn("Do not modify any files", result[-1])


if __name__ == "__main__":
    unittest.main()
