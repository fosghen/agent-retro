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
            return 1  # type: ignore[return-value]

        for value in (999, -1, "bad"):
            with sqlite3.connect(self.path) as connection:
                connection.execute("UPDATE digest_cursor SET run_id = ?", (value,))
            with self.assertRaisesRegex(ValueError, "invalid stored digest cursor"):
                self.store.consume_digest(invalid_result)
        self.assertFalse(called)

        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE digest_cursor SET run_id = 0")
        with self.assertRaisesRegex(TypeError, "must return a boolean"):
            self.store.consume_digest(invalid_result)
        self.assertEqual(self.cursor(), (0, 0))

        called = False
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA user_version = 6")
        with self.assertRaisesRegex(ValueError, "unsupported store version"):
            self.store.consume_digest(invalid_result)
        self.assertFalse(called)

        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA user_version = 5")
            connection.execute("DELETE FROM digest_cursor")
        with self.assertRaisesRegex(ValueError, "invalid stored digest cursor"):
            self.store.consume_digest(invalid_result)

    def test_v4_migration_failure_preserves_state_and_retries(self) -> None:
        self.store.record_daily_run(analyzed_run())
        with sqlite3.connect(self.path) as connection:
            connection.execute("DROP TABLE digest_cursor")
            connection.execute("PRAGMA user_version = 4")

        class BrokenStore(ProposalStore):
            def _migrate_v5(self, connection: sqlite3.Connection) -> None:
                super()._migrate_v5(connection)
                raise RuntimeError

        with self.assertRaises(RuntimeError):
            BrokenStore(self.path).initialize()
        with sqlite3.connect(self.path) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            cursor_table = connection.execute("PRAGMA table_info(digest_cursor)").fetchall()
            run_count = connection.execute("SELECT count(*) FROM daily_runs").fetchone()[0]
        self.assertEqual((version, cursor_table, run_count), (4, [], 1))

        self.store.initialize()
        self.assertEqual(self.cursor(), (0, 0))
