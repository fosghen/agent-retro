import sqlite3
import tempfile
import unittest
from pathlib import Path

from agent_retro.models import Proposal, ProposalRevision, ProposalStatus, StatusEvent
from agent_retro.store import ProposalStore


def proposal() -> Proposal:
    revision = ProposalRevision(1, "Title", "Rationale", "target", ())
    return Proposal(1, "fingerprint", ProposalStatus.APPROVED, revision)


def event() -> StatusEvent:
    return StatusEvent(1, "fingerprint", ProposalStatus.NEW, ProposalStatus.APPROVED, "now")


class ProposalStoreInitializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "state" / "proposals.sqlite3"

    def test_initialization_is_idempotent_and_versioned(self) -> None:
        store = ProposalStore(self.path)

        store.initialize()
        store.initialize()

        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
        self.assertEqual(tables, [("events",), ("proposals",), ("revisions",)])

    def test_corrupt_database_is_not_replaced(self) -> None:
        self.path.parent.mkdir()
        original = b"not a sqlite database"
        self.path.write_bytes(original)

        with self.assertRaises(sqlite3.DatabaseError):
            ProposalStore(self.path).initialize()

        self.assertEqual(self.path.read_bytes(), original)

    def test_proposal_revision_and_event_commit_together(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()

        store.save(proposal(), event())

        with sqlite3.connect(self.path) as connection:
            counts = tuple(
                connection.execute(query).fetchone()[0]
                for query in (
                    "SELECT count(*) FROM proposals",
                    "SELECT count(*) FROM revisions",
                    "SELECT count(*) FROM events",
                )
            )
        self.assertEqual(counts, (1, 1, 1))

    def test_locked_writer_fails_without_partial_state(self) -> None:
        store = ProposalStore(self.path, timeout=0)
        store.initialize()
        with sqlite3.connect(self.path) as blocker:
            blocker.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                store.save(proposal(), event())

        store.save(proposal(), event())

    def test_failed_migration_rolls_back_and_can_retry(self) -> None:
        class BrokenStore(ProposalStore):
            def _migrate_v1(self, connection: sqlite3.Connection) -> None:
                super()._migrate_v1(connection)
                message = "injected migration failure"
                raise RuntimeError(message)

        with self.assertRaises(RuntimeError):
            BrokenStore(self.path).initialize()

        ProposalStore(self.path).initialize()


if __name__ == "__main__":
    unittest.main()
