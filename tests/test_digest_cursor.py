import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from agent_retro.models import DailyRun, DailySessionOutcome, SessionOutcomeStatus
from agent_retro.store import ProposalStore


def analyzed_run() -> DailyRun:
    outcome = DailySessionOutcome("session-a", SessionOutcomeStatus.ANALYZED, "derived")
    return DailyRun("2026-11-03", "2026-11-03T09:00:00Z", (outcome,))


class DigestCursorTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
