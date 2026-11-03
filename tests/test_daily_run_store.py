import sqlite3
import tempfile
import unittest
from pathlib import Path

from agent_retro.models import DailyRun, DailySessionOutcome, SessionOutcomeStatus
from agent_retro.store import ProposalStore


def outcome(
    session_hash: str,
    status: SessionOutcomeStatus = SessionOutcomeStatus.ANALYZED,
    *,
    retryable: bool = False,
) -> DailySessionOutcome:
    log_ref = f"logs/{session_hash}.log" if status is SessionOutcomeStatus.FAILED else None
    return DailySessionOutcome(session_hash, status, "derived outcome", retryable, log_ref)


def run(day: int, *outcomes: DailySessionOutcome) -> DailyRun:
    date = f"2026-11-{day:02d}"
    return DailyRun(date, f"{date}T09:00:00Z", outcomes)


class DailyRunStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "state.sqlite3"
        self.store = ProposalStore(self.path)
        self.store.initialize()

    def counts(self) -> tuple[int, int]:
        with sqlite3.connect(self.path) as connection:
            return (
                connection.execute("SELECT count(*) FROM daily_runs").fetchone()[0],
                connection.execute("SELECT count(*) FROM daily_outcomes").fetchone()[0],
            )

    def test_records_and_lists_stable_run_summaries_after_cursor(self) -> None:
        first = run(2, outcome("session-a"), outcome("session-b", SessionOutcomeStatus.SKIPPED))
        second = run(3, outcome("session-c"))
        first_id = self.store.record_daily_run(first)
        second_id = self.store.record_daily_run(second)
        self.assertEqual(self.store.list_daily_runs(), [(first_id, first), (second_id, second)])
        self.assertEqual(self.store.list_daily_runs(after_id=first_id), [(second_id, second)])
        self.assertEqual(self.counts(), (2, 3))

    def test_retry_query_returns_only_resumable_failures_with_logs(self) -> None:
        self.store.record_daily_run(
            run(
                2,
                outcome("session-a", SessionOutcomeStatus.FAILED, retryable=True),
                outcome("session-b", SessionOutcomeStatus.FAILED, retryable=True),
            )
        )
        retryable = outcome("session-c", SessionOutcomeStatus.FAILED, retryable=True)
        self.store.record_daily_run(
            run(
                3,
                outcome("session-a"),
                outcome("session-b", SessionOutcomeStatus.FAILED),
                retryable,
            )
        )
        self.assertEqual(self.store.retryable_failures(), [retryable])

    def test_database_failure_and_forward_version_never_partially_write(self) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TRIGGER fail_outcome BEFORE INSERT ON daily_outcomes "
                "WHEN NEW.session_hash = 'session-b' "
                "BEGIN SELECT RAISE(FAIL, 'injected'); END"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.record_daily_run(run(3, outcome("session-a"), outcome("session-b")))
        self.assertEqual(self.counts(), (0, 0))

        with sqlite3.connect(self.path) as connection:
            connection.execute("DROP TRIGGER fail_outcome")
            connection.execute("PRAGMA user_version = 5")
        with self.assertRaisesRegex(ValueError, "unsupported store version"):
            self.store.record_daily_run(run(3, outcome("session-a")))
        self.assertEqual(self.counts(), (0, 0))

    def test_corrupt_outcome_and_invalid_cursor_fail_closed(self) -> None:
        run_id = self.store.record_daily_run(run(3, outcome("session-a")))
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "UPDATE daily_outcomes SET retryable = 2 WHERE run_id = ?", (run_id,)
            )
        with self.assertRaisesRegex(ValueError, "invalid stored daily outcome"):
            self.store.list_daily_runs()
        with self.assertRaisesRegex(ValueError, "after_id"):
            self.store.list_daily_runs(after_id=-1)
