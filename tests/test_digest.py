import io
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agent_retro.cli import main
from agent_retro.models import (
    DailyRun,
    DailySessionOutcome,
    EvidenceReference,
    ProposalObservation,
    SessionOutcomeStatus,
)
from agent_retro.store import ProposalStore


def outcome(
    session: str,
    status: SessionOutcomeStatus,
    *,
    retryable: bool = False,
    log: str | None = None,
) -> DailySessionOutcome:
    return DailySessionOutcome(session, status, "raw private detail", retryable, log)


class DailyDigestTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.path = root / "state.sqlite3"
        self.store = ProposalStore(self.path)
        self.store.initialize()

    def test_forward_store_version_reports_bounded_error(self) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA user_version = 6")
        with patch("agent_retro.cli._write") as write:
            self.assertEqual(main(["--store", str(self.path), "digest"]), 1)
        write.assert_called_once_with(
            "Cannot read proposal store: invalid or unsupported data.", error=True
        )

    def seed_changes(self) -> str:
        def observation(source: str) -> ProposalObservation:
            return ProposalObservation(
                "Improve review",
                "agent-retro",
                "one skill",
                EvidenceReference(source, "private evidence"),
            )

        self.store.aggregate_observation(observation("source-a"))
        proposal = self.store.aggregate_observation(
            observation("source-b"), occurred_at="created-at"
        )
        if proposal is None:
            self.fail("proposal was not promoted")
        self.store.approve(proposal.fingerprint, 1, "approved-at")
        first = DailyRun(
            "2026-11-02",
            "first",
            (
                outcome("private-a", SessionOutcomeStatus.FAILED, retryable=True, log="logs/a.log"),
                outcome("private-b", SessionOutcomeStatus.FAILED, retryable=True, log="logs/b.log"),
            ),
        )
        second = DailyRun(
            "2026-11-03",
            "second",
            (
                outcome("private-a", SessionOutcomeStatus.ANALYZED),
                outcome("private-b", SessionOutcomeStatus.FAILED, log="logs/b-final.log"),
                outcome("private-c", SessionOutcomeStatus.FAILED, retryable=True, log="logs/c.log"),
                outcome("private-d", SessionOutcomeStatus.SKIPPED),
            ),
        )
        self.store.record_daily_run(first)
        self.store.record_daily_run(second)
        return proposal.fingerprint

    def run_digest(self) -> str:
        output_stream = io.StringIO()
        with redirect_stdout(output_stream):
            self.assertEqual(main(["--store", str(self.path), "digest"]), 0)
        return output_stream.getvalue()
