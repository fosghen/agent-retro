import io
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from agent_retro.cli import main
from agent_retro.models import (
    EvidenceReference,
    Proposal,
    ProposalRevision,
    ProposalStatus,
    StatusEvent,
)
from agent_retro.store import ProposalStore


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store_path = Path(self.temporary.name) / "proposals.sqlite3"

    def save_proposal(self) -> None:
        store = ProposalStore(self.store_path)
        store.initialize()
        proposal = Proposal(
            1,
            "workflow:retro:scope",
            ProposalStatus.NEW,
            ProposalRevision(
                1,
                "Bound evidence",
                "Protect privacy",
                "SKILL.md",
                tuple(EvidenceReference("s" * 129, "x" * 501) for _ in range(6)),
                "Repeated failures",
                "Retrospectives",
                "SKILL.md edit",
                "Fewer failures",
                "False positives",
                "One skill",
                "Run evaluations",
            ),
        )
        event = StatusEvent(1, proposal.fingerprint, proposal.status, proposal.status, "now")
        store.save(proposal, event)

    def test_help_exits_successfully(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("Local-first retrospectives", output.getvalue())

    def test_list_filters_and_summarizes_proposals(self) -> None:
        self.save_proposal()
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["--store", str(self.store_path), "list", "--status", "new"])
        self.assertEqual(result, 0)
        self.assertIn("workflow:retro:scope\tnew\tBound evidence", output.getvalue())

    def test_show_presents_reviewable_fields(self) -> None:
        self.save_proposal()
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["--store", str(self.store_path), "show", "workflow:retro:scope"])
        self.assertEqual(result, 0)
        for expected in (
            "Problem: Repeated failures",
            "Affected workflow: Retrospectives",
            "Proposed artifact: SKILL.md edit",
            "Expected benefit: Fewer failures",
            "Risks: False positives",
            "Scope: One skill",
            "Validation: Run evaluations",
        ):
            self.assertIn(expected, output.getvalue())
        self.assertIn("Additional evidence omitted", output.getvalue())
        self.assertNotIn("s" * 129, output.getvalue())
        self.assertNotIn("x" * 501, output.getvalue())


if __name__ == "__main__":
    unittest.main()
