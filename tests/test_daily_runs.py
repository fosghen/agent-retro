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
