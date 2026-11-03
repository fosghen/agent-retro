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
