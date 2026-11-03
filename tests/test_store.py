import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from agent_retro.models import (
    EvidenceReference,
    Proposal,
    ProposalObservation,
    ProposalRevision,
    ProposalStatus,
    StatusEvent,
)
from agent_retro.store import ProposalStore


def proposal() -> Proposal:
    revision = ProposalRevision(1, "Title", "Rationale", "target", ())
    return Proposal(1, "fingerprint", ProposalStatus.APPROVED, revision)


def event() -> StatusEvent:
    return StatusEvent(1, "fingerprint", ProposalStatus.NEW, ProposalStatus.APPROVED, "now")


def observation(source_hash: str, *, scope: str = "one file") -> ProposalObservation:
    return ProposalObservation(
        "Improve review", "agent-retro", scope, EvidenceReference(source_hash, "bounded")
    )


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
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 4)
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
        self.assertEqual(
            tables,
            [
                ("daily_outcomes",),
                ("daily_runs",),
                ("decisions",),
                ("events",),
                ("occurrences",),
                ("proposals",),
                ("revisions",),
            ],
        )

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

    def test_lists_proposals_in_stable_order_with_status_filter(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        approved = proposal()
        new = Proposal(
            1,
            "another",
            ProposalStatus.NEW,
            ProposalRevision(1, "Another", "Reason", "target", ()),
        )
        store.save(approved, event())
        store.save(
            new,
            StatusEvent(1, "another", ProposalStatus.NEW, ProposalStatus.NEW, "now"),
        )

        self.assertEqual(
            [item.fingerprint for item in store.list_proposals()],
            ["another", "fingerprint"],
        )
        self.assertEqual(store.list_proposals(ProposalStatus.APPROVED), [approved])

    def test_get_returns_current_revision_or_none(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        store.save(proposal(), event())

        self.assertEqual(store.get("fingerprint"), proposal())
        self.assertIsNone(store.get("missing"))

    def test_read_rejects_corrupt_relation_and_forward_version(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        store.save(proposal(), event())
        with sqlite3.connect(self.path) as connection:
            connection.execute("DELETE FROM revisions")
        with self.assertRaises(ValueError):
            store.list_proposals()

        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA user_version = 5")
        with self.assertRaisesRegex(ValueError, "unsupported store version"):
            store.get("fingerprint")

    def test_records_distinct_observations_idempotently(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        first = observation("source-a")
        second = observation("source-b")

        self.assertTrue(store.record_observation(first))
        self.assertFalse(store.record_observation(first))
        self.assertTrue(store.record_observation(second))
        self.assertEqual(store.occurrence_count(first.fingerprint), 2)
        self.assertEqual(store.list_observations(first.fingerprint), [first, second])

    def test_material_scope_has_separate_history(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        first = observation("source-a")
        other = observation("source-b", scope="two files")
        store.record_observation(first)
        store.record_observation(other)
        self.assertEqual(store.list_observations(first.fingerprint), [first])
        self.assertEqual(store.list_observations(other.fingerprint), [other])

    def test_failed_v2_migration_rolls_back_and_can_retry(self) -> None:
        store = ProposalStore(self.path)
        self.path.parent.mkdir(parents=True)
        with sqlite3.connect(self.path) as connection:
            store._migrate_v1(connection)  # noqa: SLF001 -- build a real legacy database.
        store.save(proposal(), event())

        class BrokenStore(ProposalStore):
            def _migrate_v2(self, connection: sqlite3.Connection) -> None:
                super()._migrate_v2(connection)
                raise RuntimeError

        with self.assertRaises(RuntimeError):
            BrokenStore(self.path).initialize()
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT count(*) FROM proposals").fetchone()[0], 1)
            self.assertIsNone(
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE name = 'occurrences'"
                ).fetchone()
            )
        store.initialize()
        self.assertEqual(store.get("fingerprint"), proposal())

    def test_forward_version_rejects_observation_before_write(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA user_version = 5")
        with self.assertRaisesRegex(ValueError, "unsupported store version"):
            store.record_observation(observation("source-a"))
        with sqlite3.connect(self.path) as connection:
            count = connection.execute("SELECT count(*) FROM occurrences").fetchone()[0]
        self.assertEqual(count, 0)

    def test_second_observation_promotes_once_and_third_revises(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        first, second, third = (observation(f"source-{value}") for value in "abc")

        self.assertIsNone(store.aggregate_observation(first))
        self.assertIsNone(store.aggregate_observation(first))
        promoted = store.aggregate_observation(second)
        self.assertEqual(promoted.status, ProposalStatus.NEW)
        self.assertEqual(promoted.revision.number, 1)
        self.assertEqual(store.aggregate_observation(second), promoted)
        revised = store.aggregate_observation(third)
        self.assertEqual(revised.revision.number, 2)
        self.assertEqual(
            [item.source_hash for item in revised.revision.evidence],
            ["source-a", "source-b", "source-c"],
        )
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM proposals").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT count(*) FROM revisions").fetchone()[0], 2)
            payloads = connection.execute(
                "SELECT payload FROM revisions WHERE fingerprint = ? ORDER BY revision",
                (promoted.fingerprint,),
            ).fetchall()
        evidence = [
            [item["source_hash"] for item in json.loads(row[0])["evidence"]] for row in payloads
        ]
        self.assertEqual(evidence, [["source-a", "source-b"], ["source-a", "source-b", "source-c"]])

    def test_aggregation_bounds_evidence_and_separates_scope(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        proposal = None
        for index in range(7):
            proposal = store.aggregate_observation(observation(f"source-{index}"))
        self.assertEqual(
            [item.source_hash for item in proposal.revision.evidence],
            [f"source-{index}" for index in range(2, 7)],
        )

        other = store.aggregate_observation(observation("other-a", scope="two files"))
        self.assertIsNone(other)
        other = store.aggregate_observation(observation("other-b", scope="two files"))
        self.assertNotEqual(proposal.fingerprint, other.fingerprint)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM proposals").fetchone()[0], 2)

    def test_aggregation_resumes_existing_history(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        first, second = observation("source-a"), observation("source-b")
        store.record_observation(first)
        store.record_observation(second)

        promoted = store.aggregate_observation(second)
        self.assertEqual(promoted.revision.number, 1)

    def test_aggregation_revises_approved_proposal_without_changing_status(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        store.aggregate_observation(observation("source-a"))
        promoted = store.aggregate_observation(observation("source-b"))
        approved = promoted.transition(ProposalStatus.APPROVED)
        store.save(
            approved,
            StatusEvent(
                1, approved.fingerprint, ProposalStatus.NEW, ProposalStatus.APPROVED, "now"
            ),
        )

        result = store.aggregate_observation(observation("source-c"))
        self.assertEqual(result.status, ProposalStatus.APPROVED)
        self.assertEqual(result.revision.number, 2)
        self.assertEqual(store.occurrence_count(approved.fingerprint), 3)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM revisions").fetchone()[0], 2)

    def test_aggregation_rolls_back_observation_on_failure(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        first, second = observation("source-a"), observation("source-b")
        store.aggregate_observation(first)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TRIGGER fail_proposal BEFORE INSERT ON proposals "
                "BEGIN SELECT RAISE(ABORT, 'injected'); END"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            store.aggregate_observation(second)
        self.assertEqual(store.occurrence_count(first.fingerprint), 1)
        self.assertIsNone(store.get(first.fingerprint))
        with sqlite3.connect(self.path) as connection:
            connection.execute("DROP TRIGGER fail_proposal")
        self.assertEqual(store.aggregate_observation(second).revision.number, 1)
        self.assertEqual(store.occurrence_count(first.fingerprint), 2)
        with sqlite3.connect(self.path) as connection:
            counts = (
                connection.execute("SELECT count(*) FROM proposals").fetchone()[0],
                connection.execute("SELECT count(*) FROM revisions").fetchone()[0],
            )
        self.assertEqual(counts, (1, 1))

    def test_rejected_duplicate_stays_suppressed(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        store.aggregate_observation(observation("source-a"))
        promoted = store.aggregate_observation(observation("source-b"))
        rejected = promoted.transition(ProposalStatus.REJECTED)
        store.save(
            rejected,
            StatusEvent(
                1, rejected.fingerprint, ProposalStatus.NEW, ProposalStatus.REJECTED, "rejected"
            ),
        )

        self.assertEqual(store.aggregate_observation(observation("source-b")), rejected)
        with sqlite3.connect(self.path) as connection:
            counts = tuple(
                connection.execute(query).fetchone()[0]
                for query in (
                    "SELECT count(*) FROM occurrences",
                    "SELECT count(*) FROM revisions",
                    "SELECT count(*) FROM events",
                )
            )
        self.assertEqual(counts, (2, 1, 1))

    def test_new_evidence_reopens_rejected_proposal_once(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        store.aggregate_observation(observation("source-a"))
        promoted = store.aggregate_observation(observation("source-b"))
        rejected = promoted.transition(ProposalStatus.REJECTED)
        store.save(
            rejected,
            StatusEvent(
                1, rejected.fingerprint, ProposalStatus.NEW, ProposalStatus.REJECTED, "rejected"
            ),
        )

        reopened = store.aggregate_observation(observation("source-c"), occurred_at="new-evidence")
        self.assertEqual((reopened.status, reopened.revision.number), (ProposalStatus.NEW, 2))
        self.assertEqual(
            [item.source_hash for item in reopened.revision.evidence],
            ["source-a", "source-b", "source-c"],
        )
        self.assertEqual(store.aggregate_observation(observation("source-c")), reopened)
        with sqlite3.connect(self.path) as connection:
            event = connection.execute(
                "SELECT previous, current, occurred_at FROM events ORDER BY id DESC LIMIT 1"
            ).fetchone()
            counts = tuple(
                connection.execute(query).fetchone()[0]
                for query in (
                    "SELECT count(*) FROM occurrences",
                    "SELECT count(*) FROM revisions",
                    "SELECT count(*) FROM events",
                )
            )
            payloads = connection.execute(
                "SELECT payload FROM revisions ORDER BY revision"
            ).fetchall()
        self.assertEqual(event, ("rejected", "new", "new-evidence"))
        self.assertEqual(counts, (3, 2, 2))
        evidence = [
            [item["source_hash"] for item in json.loads(row[0])["evidence"]] for row in payloads
        ]
        self.assertEqual(evidence, [["source-a", "source-b"], ["source-a", "source-b", "source-c"]])

    def test_changed_scope_does_not_reopen_rejected_proposal(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        store.aggregate_observation(observation("source-a"))
        promoted = store.aggregate_observation(observation("source-b"))
        rejected = promoted.transition(ProposalStatus.REJECTED)
        store.save(
            rejected,
            StatusEvent(
                1, rejected.fingerprint, ProposalStatus.NEW, ProposalStatus.REJECTED, "rejected"
            ),
        )

        store.aggregate_observation(observation("other-a", scope="two files"))
        other = store.aggregate_observation(observation("other-b", scope="two files"))
        self.assertEqual(store.get(rejected.fingerprint), rejected)
        self.assertEqual((other.status, other.revision.number), (ProposalStatus.NEW, 1))
        self.assertNotEqual(other.fingerprint, rejected.fingerprint)

    def test_reopen_failure_rolls_back_new_evidence(self) -> None:
        store = ProposalStore(self.path)
        store.initialize()
        store.aggregate_observation(observation("source-a"))
        promoted = store.aggregate_observation(observation("source-b"))
        rejected = promoted.transition(ProposalStatus.REJECTED)
        store.save(
            rejected,
            StatusEvent(
                1, rejected.fingerprint, ProposalStatus.NEW, ProposalStatus.REJECTED, "rejected"
            ),
        )
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TRIGGER fail_revision BEFORE INSERT ON revisions "
                "BEGIN SELECT RAISE(ABORT, 'injected'); END"
            )

        with self.assertRaises(sqlite3.IntegrityError):
            store.aggregate_observation(observation("source-c"), occurred_at="new-evidence")
        self.assertEqual(store.get(rejected.fingerprint), rejected)
        self.assertEqual(store.occurrence_count(rejected.fingerprint), 2)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM events").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
