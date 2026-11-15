import subprocess
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.daily_codex_retro import activity_files, command, parse_day, run_day, session_dir


class DailyCodexRetroTests(unittest.TestCase):
    def active_home(self, temporary: str) -> Path:
        home = Path(temporary)
        source = session_dir(home, date(2026, 11, 6))
        source.mkdir(parents=True)
        (source / "session.jsonl").write_text('{"timestamp":"2026-11-06T12:00:00+00:00"}\n')
        return home

    def test_session_directory_uses_codex_date_partition(self) -> None:
        path = session_dir(Path("/home/test"), date(2026, 11, 2))
        self.assertEqual(path, Path("/home/test/.codex/sessions/2026/11/02"))

    def test_command_is_read_only_and_writes_requested_report(self) -> None:
        report = Path("/reports/retro.md")
        with patch("scripts.daily_codex_retro.shutil.which", return_value="/bin/codex"):
            result = command(
                Path("/home/test"), date(2026, 11, 2), report, (Path("/sessions/a.jsonl"),)
            )
        self.assertEqual(result[0:2], ["/bin/codex", "exec"])
        self.assertIn("gpt-6-luna", result)
        self.assertIn('model_reasoning_effort="medium"', result)
        self.assertIn("read-only", result)
        self.assertIn(str(report), result)
        self.assertIn("2026-11-02", result[-1])
        self.assertIn("/sessions/a.jsonl", result[-1])
        self.assertIn("session_id", result[-1])
        self.assertIn("Do not modify any files", result[-1])

    def test_activity_files_follow_events_across_date_partitions(self) -> None:
        with TemporaryDirectory() as temporary:
            home = Path(temporary)
            previous = session_dir(home, date(2026, 11, 12))
            previous.mkdir(parents=True)
            active = previous / "continued.jsonl"
            active.write_text(
                '{"timestamp":"2026-11-12T23:59:59+00:00"}\n'
                '{"timestamp":"2026-11-13T12:00:00+00:00"}\n'
            )
            inactive = previous / "inactive.jsonl"
            inactive.write_text('{"timestamp":"2026-11-12T12:00:00+00:00"}\n')

            self.assertEqual(activity_files(home, date(2026, 11, 13)), (active,))

    def test_parse_day_defaults_to_yesterday(self) -> None:
        self.assertEqual(parse_day([], date(2026, 11, 11)), date(2026, 11, 10))

    def test_parse_day_accepts_exact_iso_date(self) -> None:
        result = parse_day(["--date", "2026-11-06"], date(2026, 11, 11))
        self.assertEqual(result, date(2026, 11, 6))

    def test_parse_day_rejects_invalid_date(self) -> None:
        with self.assertRaises(SystemExit):
            parse_day(["--date", "2026-02-30"], date(2026, 11, 11))

    def test_run_day_skips_empty_session_directory(self) -> None:
        with TemporaryDirectory() as temporary:
            home = Path(temporary)
            with patch("scripts.daily_codex_retro.subprocess.run") as execute:
                self.assertEqual(run_day(home, date(2026, 11, 6)), 0)
            execute.assert_not_called()
            self.assertFalse((home / ".codex/worklog/retros").exists())

    def test_run_day_uses_selected_date_for_report(self) -> None:
        with TemporaryDirectory() as temporary:
            home = self.active_home(temporary)

            def complete(arguments: list[str], *, check: bool) -> None:
                self.assertTrue(check)
                output = Path(arguments[arguments.index("--output-last-message") + 1])
                output.write_text("fresh report\n")

            with (
                patch("scripts.daily_codex_retro.shutil.which", return_value="/bin/codex"),
                patch("scripts.daily_codex_retro.subprocess.run", side_effect=complete),
            ):
                self.assertEqual(run_day(home, date(2026, 11, 6)), 0)
            report = home / ".codex/worklog/retros/2026-11-06-daily.md"
            self.assertEqual(report.read_text(), "fresh report\n")

    def test_failed_run_preserves_existing_report(self) -> None:
        with TemporaryDirectory() as temporary:
            home = self.active_home(temporary)
            report = home / ".codex/worklog/retros/2026-11-06-daily.md"
            report.parent.mkdir(parents=True)
            report.write_text("previous\n")

            def fail(arguments: list[str], *, check: bool) -> None:
                self.assertTrue(check)
                output = Path(arguments[arguments.index("--output-last-message") + 1])
                output.write_text("")
                raise subprocess.CalledProcessError(1, arguments)

            with (
                patch("scripts.daily_codex_retro.shutil.which", return_value="/bin/codex"),
                patch("scripts.daily_codex_retro.subprocess.run", side_effect=fail),
                self.assertRaises(subprocess.CalledProcessError),
            ):
                run_day(home, date(2026, 11, 6))
            self.assertEqual(report.read_text(), "previous\n")

    def test_empty_success_preserves_existing_report(self) -> None:
        with TemporaryDirectory() as temporary:
            home = self.active_home(temporary)
            report = home / ".codex/worklog/retros/2026-11-06-daily.md"
            report.parent.mkdir(parents=True)
            report.write_text("previous\n")

            def empty(arguments: list[str], *, check: bool) -> None:
                self.assertTrue(check)
                output = Path(arguments[arguments.index("--output-last-message") + 1])
                output.write_text(" \n")

            with (
                patch("scripts.daily_codex_retro.shutil.which", return_value="/bin/codex"),
                patch("scripts.daily_codex_retro.subprocess.run", side_effect=empty),
                self.assertRaisesRegex(RuntimeError, "empty report"),
            ):
                run_day(home, date(2026, 11, 6))
            self.assertEqual(report.read_text(), "previous\n")


if __name__ == "__main__":
    unittest.main()
