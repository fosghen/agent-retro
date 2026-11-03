import sqlite3
import tempfile
import unittest
from pathlib import Path

from agent_retro.models import (
    MAX_RUN_OUTCOMES,
    DailyRun,
    DailySessionOutcome,
    SchemaError,
    SessionOutcomeStatus,
    daily_session_outcome_from_mapping,
)
from agent_retro.store import ProposalStore


class DailyRunSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "state.sqlite3"
        self.store = ProposalStore(self.path)
        self.store.initialize()

    def test_run_rejects_invalid_dates_and_duplicate_sessions(self) -> None:
        outcome = DailySessionOutcome(
            "sha256:session-a", SessionOutcomeStatus.ANALYZED, "validated"
        )
        with self.assertRaises(SchemaError):
            DailyRun("2026-02-30", "now", ())
        with self.assertRaises(SchemaError):
            DailyRun("2026-11-03", "now", (outcome, outcome))
        with self.assertRaises(SchemaError):
            DailyRun("2026-11-03", "now", (outcome,) * (MAX_RUN_OUTCOMES + 1))
