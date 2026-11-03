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

    def test_models_accept_only_bounded_privacy_safe_metadata(self) -> None:
        failed = daily_session_outcome_from_mapping(
            {
                "session_hash": "sha256:session-a",
                "status": "failed",
                "detail": "analyzer unavailable",
                "retryable": False,
                "log_ref": "logs/2026-11-03-session-a.log",
            }
        )
        self.assertIsInstance(DailyRun("2026-11-03", "2026-11-03T09:00:00Z", (failed,)), DailyRun)

        base = {"session_hash": "s", "status": "analyzed", "detail": "safe"}
        invalid = (
            base | {"session_hash": ""},
            base | {"status": "failed"},
            base | {"status": "failed", "retryable": True, "log_ref": "../transcript.log"},
            base | {"status": "failed", "retryable": True, "log_ref": "logs/./failure.log"},
            base | {"transcript": "private raw content"},
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(SchemaError):
                daily_session_outcome_from_mapping(value)
        with self.assertRaises(SchemaError):
            DailySessionOutcome("s", SessionOutcomeStatus.SKIPPED, "safe", retryable=True)
