import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from agent_retro.models import ProposalStatus, SchemaError, analyzer_candidate_from_mapping
from agent_retro.store import ProposalStore


def candidate(source_hash: str = "source-a") -> dict[str, object]:
    return {
        "schema_version": 1,
        "intent": "Improve review",
        "target": "agent-retro",
        "scope": "one skill",
        "evidence": {"source_hash": source_hash, "excerpt": "bounded"},
        "title": "Improve review quality",
        "rationale": "Repeated review gaps",
        "problem": "Reviews miss edge cases",
        "affected_workflow": "Code review",
        "proposed_artifact": "Reviewer rule",
        "expected_benefit": "Fewer regressions",
        "risks": "False positives",
        "validation": "Run evaluations",
    }


class AnalyzerCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "state.sqlite3"
        self.store = ProposalStore(self.path)
        self.store.initialize()

    def counts(self) -> tuple[int, int, int, int]:
        with sqlite3.connect(self.path) as connection:
            return tuple(
                connection.execute(query).fetchone()[0]
                for query in (
                    "SELECT count(*) FROM occurrences",
                    "SELECT count(*) FROM proposals",
                    "SELECT count(*) FROM revisions",
                    "SELECT count(*) FROM events",
                )
            )

    def test_valid_candidates_promote_with_review_fields(self) -> None:
        self.assertIsNone(self.store.ingest_analyzer_output(candidate()))
        proposal = self.store.ingest_analyzer_output(candidate("source-b"))

        self.assertEqual(proposal.status, ProposalStatus.NEW)
        expected = analyzer_candidate_from_mapping(candidate()).revision()
        self.assertEqual(replace(proposal.revision, evidence=()), expected)
        self.assertEqual(self.counts(), (2, 1, 1, 0))

        changed = candidate("source-c")
        changed["title"] = "Updated review rule"
        revised = self.store.ingest_analyzer_output(changed)
        self.assertEqual(
            (revised.revision.number, revised.revision.title), (2, "Updated review rule")
        )
        self.assertEqual(len(revised.revision.evidence), 3)

    def test_parser_rejects_missing_review_field(self) -> None:
        value = candidate()
        value.pop("validation")

        with self.assertRaisesRegex(SchemaError, "validation"):
            analyzer_candidate_from_mapping(value)
