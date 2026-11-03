import io
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from agent_retro.cli import main
from agent_retro.models import EvidenceReference, ProposalObservation, ProposalStatus, SchemaError
from agent_retro.store import ProposalStore


def observation(source_hash: str) -> ProposalObservation:
    return ProposalObservation(
        "Improve review", "agent-retro", "one skill", EvidenceReference(source_hash, "bounded")
    )


class RejectDeferTests(unittest.TestCase):
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

    def test_rejection_suppresses_duplicates_and_new_evidence_reopens(self) -> None:
        rejected = self.store.reject(self.proposal.fingerprint, "Not actionable", "rejected-at")
        self.assertEqual(rejected.status, ProposalStatus.REJECTED)
        with self.assertRaises(SchemaError):
            self.store.reject(self.proposal.fingerprint, "Again", "again-at")
        self.assertEqual(self.store.aggregate_observation(observation("source-b")), rejected)
        self.assertEqual(self.counts(), (1, 2))

        reopened = self.store.aggregate_observation(observation("source-c"), occurred_at="new-at")
        self.assertEqual(reopened.status, ProposalStatus.NEW)
        with sqlite3.connect(self.path) as connection:
            decision = connection.execute(
                "SELECT decision, revision, occurred_at, reason, until_date FROM decisions"
            ).fetchone()
            event_times = connection.execute(
                "SELECT occurred_at FROM events WHERE previous != current ORDER BY id"
            ).fetchall()
        self.assertEqual(decision, ("rejected", 1, "rejected-at", "Not actionable", None))
        self.assertEqual(event_times, [("rejected-at",), ("new-at",)])
        self.assertEqual(self.counts(), (1, 3))

    def test_invalid_rejection_and_database_failure_are_atomic(self) -> None:
        for reason in ("", "x" * 1001):
            with self.subTest(reason=reason), self.assertRaises(SchemaError):
                self.store.reject(self.proposal.fingerprint, reason, "now")
        self.assertEqual(self.counts(), (0, 1))

        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TRIGGER fail_reject BEFORE UPDATE ON proposals "
                "BEGIN SELECT RAISE(FAIL, 'injected'); END"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.reject(self.proposal.fingerprint, "Valid", "now")
        self.assertEqual(self.counts(), (0, 1))
        self.assertEqual(self.store.get(self.proposal.fingerprint).status, ProposalStatus.NEW)

    def test_deferral_requires_iso_date_and_repeated_decision_is_atomic(self) -> None:
        for until_date in ("", "2026-02-30", "03-11-2026"):
            with self.subTest(until_date=until_date), self.assertRaises(SchemaError):
                self.store.defer(self.proposal.fingerprint, until_date, "now")
        self.assertEqual(self.counts(), (0, 1))

        deferred = self.store.defer(self.proposal.fingerprint, "2026-12-01", "deferred-at")
        self.assertEqual(deferred.status, ProposalStatus.DEFERRED)
        with self.assertRaises(SchemaError):
            self.store.defer(self.proposal.fingerprint, "2026-12-02", "again")
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT decision, occurred_at, reason, until_date FROM decisions"
            ).fetchone()
        self.assertEqual(row, ("deferred", "deferred-at", None, "2026-12-01"))
        self.assertEqual(self.counts(), (1, 2))

    def test_cli_rejects_and_reports_invalid_deferral_without_traceback(self) -> None:
        result = main(
            ["--store", str(self.path), "reject", self.proposal.fingerprint, "--reason", "Noise"]
        )
        self.assertEqual(result, 0)
        self.assertEqual(self.store.get(self.proposal.fingerprint).status, ProposalStatus.REJECTED)

        error = io.StringIO()
        with redirect_stderr(error):
            result = main(
                ["--store", str(self.path), "defer", self.proposal.fingerprint, "--until", "bad"]
            )
        self.assertEqual(result, 1)
        self.assertIn("Cannot update proposal", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()
