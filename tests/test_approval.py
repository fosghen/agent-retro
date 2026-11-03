import sqlite3
import tempfile
import unittest
from pathlib import Path

from agent_retro.cli import main
from agent_retro.models import (
    EvidenceReference,
    ProposalObservation,
    ProposalStatus,
    SchemaError,
    StatusEvent,
)
from agent_retro.store import ProposalStore


def observation(source_hash: str) -> ProposalObservation:
    return ProposalObservation(
        "Improve review", "agent-retro", "one skill", EvidenceReference(source_hash, "bounded")
    )


class ApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "state.sqlite3"
        self.store = ProposalStore(self.path)
        self.store.initialize()
        self.store.aggregate_observation(observation("source-a"))
        self.proposal = self.store.aggregate_observation(observation("source-b"))

    def counts(self) -> tuple[int, int]:
        with sqlite3.connect(self.path) as connection:
            return (
                connection.execute("SELECT count(*) FROM decisions").fetchone()[0],
                connection.execute("SELECT count(*) FROM events").fetchone()[0],
            )

    def test_approval_freezes_reviewed_revision_across_new_evidence(self) -> None:
        approved = self.store.approve(self.proposal.fingerprint, 1, "2026-11-03T10:00:00Z")
        self.assertEqual(approved.status, ProposalStatus.APPROVED)
        frozen = self.store.approved_revision(self.proposal.fingerprint)
        self.assertEqual(frozen, self.proposal.revision)

        revised = self.store.aggregate_observation(observation("source-c"))
        self.assertEqual(revised.revision.number, 2)
        self.assertEqual(self.store.approved_revision(self.proposal.fingerprint), frozen)
        self.assertEqual(self.counts(), (1, 2))
        with sqlite3.connect(self.path) as connection:
            decision = connection.execute("SELECT revision, occurred_at FROM decisions").fetchone()
            event_time = connection.execute(
                "SELECT occurred_at FROM events WHERE previous != current"
            ).fetchone()[0]
        self.assertEqual(decision, (1, "2026-11-03T10:00:00Z"))
        self.assertEqual(event_time, "2026-11-03T10:00:00Z")

    def test_invalid_and_repeated_approval_are_atomic(self) -> None:
        with self.assertRaises(SchemaError):
            self.store.approve(self.proposal.fingerprint, 1, "")
        with self.assertRaises(SchemaError):
            self.store.approve("missing", 1, "now")
        self.assertEqual(self.counts(), (0, 1))

        self.store.approve(self.proposal.fingerprint, 1, "now")
        with self.assertRaises(SchemaError):
            self.store.approve(self.proposal.fingerprint, 1, "again")
        self.assertEqual(self.counts(), (1, 2))

    def test_stale_revision_and_database_failure_roll_back(self) -> None:
        self.store.aggregate_observation(observation("source-c"))
        with self.assertRaisesRegex(SchemaError, "stale"):
            self.store.approve(self.proposal.fingerprint, 1, "now")
        self.assertEqual(self.counts(), (0, 1))

        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TRIGGER fail_approval BEFORE UPDATE ON proposals "
                "BEGIN SELECT RAISE(FAIL, 'injected'); END"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.approve(self.proposal.fingerprint, 2, "now")
        self.assertEqual(self.counts(), (0, 1))
        with sqlite3.connect(self.path) as connection:
            state = connection.execute("SELECT status, current_revision FROM proposals").fetchone()
        self.assertEqual(state, ("new", 2))

    def test_forward_store_version_is_never_read_or_mutated(self) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA user_version = 5")
        with self.assertRaisesRegex(ValueError, "unsupported store version"):
            self.store.approve(self.proposal.fingerprint, 1, "now")
        with self.assertRaisesRegex(ValueError, "unsupported store version"):
            self.store.approved_revision(self.proposal.fingerprint)
        self.assertEqual(self.counts(), (0, 1))

    def test_v2_migration_rolls_back_and_preserves_existing_data(self) -> None:
        self.store.save(
            self.proposal,
            StatusEvent(
                1, self.proposal.fingerprint, ProposalStatus.NEW, ProposalStatus.NEW, "old"
            ),
        )
        with sqlite3.connect(self.path) as connection:
            connection.execute("DROP TABLE daily_outcomes")
            connection.execute("DROP TABLE daily_runs")
            connection.execute("DROP TABLE decisions")
            connection.execute("PRAGMA user_version = 2")

        class BrokenStore(ProposalStore):
            def _migrate_v3(self, connection: sqlite3.Connection) -> None:
                super()._migrate_v3(connection)
                message = "injected migration failure"
                raise RuntimeError(message)

        with self.assertRaises(RuntimeError):
            BrokenStore(self.path).initialize()
        with sqlite3.connect(self.path) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            decision_table = connection.execute(
                "SELECT count(*) FROM sqlite_master WHERE name = 'decisions'"
            ).fetchone()[0]
            counts = tuple(
                connection.execute(query).fetchone()[0]
                for query in (
                    "SELECT count(*) FROM occurrences",
                    "SELECT count(*) FROM proposals",
                    "SELECT count(*) FROM revisions",
                    "SELECT count(*) FROM events",
                )
            )
        self.assertEqual((version, decision_table, counts), (2, 0, (2, 1, 1, 2)))
        ProposalStore(self.path).initialize()
        self.assertEqual(ProposalStore(self.path).get(self.proposal.fingerprint), self.proposal)

    def test_cli_approves_current_revision(self) -> None:
        result = main(
            ["--store", str(self.path), "approve", self.proposal.fingerprint, "--revision", "1"]
        )
        self.assertEqual(result, 0)
        self.assertEqual(self.store.get(self.proposal.fingerprint).status, ProposalStatus.APPROVED)


if __name__ == "__main__":
    unittest.main()
