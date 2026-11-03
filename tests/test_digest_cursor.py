import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from agent_retro.models import DailyRun, DailySessionOutcome, SessionOutcomeStatus
from agent_retro.store import ProposalStore


def analyzed_run() -> DailyRun:
    outcome = DailySessionOutcome("session-a", SessionOutcomeStatus.ANALYZED, "derived")
    return DailyRun("2026-11-03", "2026-11-03T09:00:00Z", (outcome,))


class DigestCursorTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.path = root / "state.sqlite3"
        self.store = ProposalStore(self.path, timeout=1)
        self.store.initialize()

    def cursor(self) -> tuple[int, int]:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute("SELECT run_id, event_id FROM digest_cursor").fetchone()
        if row is None:
            self.fail("missing digest cursor")
        return int(row[0]), int(row[1])

    def test_consumer_failure_rolls_back_cursor_for_retry(self) -> None:
        self.store.record_daily_run(analyzed_run())

        def fail(_runs: object, _changes: object) -> bool:
            raise RuntimeError

        with self.assertRaises(RuntimeError):
            self.store.consume_digest(fail)
        self.assertEqual(self.cursor(), (0, 0))

        seen: list[int] = []

        def succeed(runs: tuple[DailyRun, ...], _changes: object) -> bool:
            seen.append(len(runs))
            return bool(runs)

        self.assertTrue(self.store.consume_digest(succeed))
        self.assertEqual((seen, self.cursor()), ([1], (1, 0)))
