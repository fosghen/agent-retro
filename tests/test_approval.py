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
        self.assertEqual(self.counts(), (1, 1))
        with sqlite3.connect(self.path) as connection:
            decision = connection.execute("SELECT revision, occurred_at FROM decisions").fetchone()
            event_time = connection.execute("SELECT occurred_at FROM events").fetchone()[0]
        self.assertEqual(decision, (1, "2026-11-03T10:00:00Z"))
        self.assertEqual(event_time, "2026-11-03T10:00:00Z")

    def test_invalid_and_repeated_approval_are_atomic(self) -> None:
        with self.assertRaises(SchemaError):
            self.store.approve(self.proposal.fingerprint, 1, "")
        with self.assertRaises(SchemaError):
            self.store.approve("missing", 1, "now")
        self.assertEqual(self.counts(), (0, 0))

        self.store.approve(self.proposal.fingerprint, 1, "now")
        with self.assertRaises(SchemaError):
            self.store.approve(self.proposal.fingerprint, 1, "again")
        self.assertEqual(self.counts(), (1, 1))
