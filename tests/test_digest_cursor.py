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

    def test_concurrent_consumers_emit_one_snapshot(self) -> None:
        self.store.record_daily_run(analyzed_run())
        events = (threading.Event() for _ in range(4))
        entered, release, second_started, second_called = events
        outputs: list[str] = []
        errors: list[Exception] = []

        def first(runs: tuple[DailyRun, ...], _changes: object) -> bool:
            outputs.append(f"first:{len(runs)}")
            entered.set()
            release.wait(1)
            return bool(runs)

        def second(runs: tuple[DailyRun, ...], _changes: object) -> bool:
            second_called.set()
            if runs:
                outputs.append(f"second:{len(runs)}")
            return bool(runs)

        def consume(callback: object, started: threading.Event | None = None) -> None:
            try:
                if started is not None:
                    started.set()
                self.store.consume_digest(callback)  # type: ignore[arg-type]
            except Exception as error:  # noqa: BLE001 -- surface thread failures in test.
                errors.append(error)

        first_thread = threading.Thread(target=consume, args=(first,))
        second_thread = threading.Thread(target=consume, args=(second, second_started))
        first_thread.start()
        self.assertTrue(entered.wait(1))
        second_thread.start()
        self.assertTrue(second_started.wait(1))
        self.assertFalse(second_called.wait(0.05))
        release.set()
        first_thread.join(1)
        second_thread.join(1)

        self.assertFalse(first_thread.is_alive() or second_thread.is_alive())
        self.assertTrue(second_called.is_set())
        self.assertEqual((outputs, errors, self.cursor()), (["first:1"], [], (1, 0)))

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

    def test_corrupt_cursor_and_consumer_result_fail_closed(self) -> None:
        self.store.record_daily_run(analyzed_run())
        called = False

        def invalid_result(_runs: object, _changes: object) -> bool:
            nonlocal called
            called = True
