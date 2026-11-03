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
        self.assertEqual(self.counts(), (1, 1))

        reopened = self.store.aggregate_observation(observation("source-c"), occurred_at="new-at")
        self.assertEqual(reopened.status, ProposalStatus.NEW)
        with sqlite3.connect(self.path) as connection:
            decision = connection.execute(
                "SELECT decision, revision, occurred_at, reason, until_date FROM decisions"
            ).fetchone()
            event_times = connection.execute(
                "SELECT occurred_at FROM events ORDER BY id"
            ).fetchall()
        self.assertEqual(decision, ("rejected", 1, "rejected-at", "Not actionable", None))
        self.assertEqual(event_times, [("rejected-at",), ("new-at",)])
        self.assertEqual(self.counts(), (1, 2))
