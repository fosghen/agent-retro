import sqlite3
import tempfile
import unittest
from pathlib import Path

from agent_retro.analyzer import AnalyzerInput, run_analyzer
from agent_retro.models import ProposalStatus, SchemaError, StatusEvent
from agent_retro.store import ProposalStore


def candidate(source_hash: str, excerpt: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "intent": "Improve review",
        "target": "agent-retro",
        "scope": "one skill",
        "evidence": {"source_hash": source_hash, "excerpt": excerpt},
        "title": "Improve review quality",
        "rationale": "Repeated review gaps",
        "problem": "Reviews miss edge cases",
        "affected_workflow": "Code review",
        "proposed_artifact": "Reviewer rule",
        "expected_benefit": "Fewer regressions",
        "risks": "False positives",
        "validation": "Run evaluations",
    }


class FakeAnalyzer:
    def __init__(self, result: object) -> None:
        self.result = result
        self.inputs: list[AnalyzerInput] = []

    def analyze(self, value: AnalyzerInput, /) -> object:
        self.inputs.append(value)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class AnalyzerPortTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = ProposalStore(Path(temporary.name) / "state.sqlite3")
        self.store.initialize()

    def assert_empty(self) -> None:
        with sqlite3.connect(self.store.path) as connection:
            counts = tuple(
                connection.execute(query).fetchone()[0]
                for query in (
                    "SELECT count(*) FROM occurrences",
                    "SELECT count(*) FROM proposals",
                    "SELECT count(*) FROM revisions",
                    "SELECT count(*) FROM events",
                )
            )
        self.assertEqual(counts, (0, 0, 0, 0))

    def test_passes_exact_bounded_normalized_input_and_promotes(self) -> None:
        first = FakeAnalyzer(candidate("source-a", "alpha beta"))
        self.assertIsNone(run_analyzer(first, self.store, " source-a ", " alpha\n beta "))
        self.assertEqual(first.inputs, [AnalyzerInput("source-a", "alpha beta")])

        long_excerpt = "x" * 501
        second = FakeAnalyzer(candidate("source-b", "x" * 500))
        proposal = run_analyzer(second, self.store, "source-b", long_excerpt)
        self.assertEqual(second.inputs, [AnalyzerInput("source-b", "x" * 500)])
        self.assertEqual(len(proposal.revision.evidence), 2)

    def test_invocation_failure_does_not_mutate_store(self) -> None:
        analyzer = FakeAnalyzer(RuntimeError("offline"))
        with self.assertRaisesRegex(RuntimeError, "offline"):
            run_analyzer(analyzer, self.store, "source-a", "evidence")
        self.assert_empty()

    def test_validation_failure_does_not_mutate_store(self) -> None:
        analyzer = FakeAnalyzer({"schema_version": 1})
        with self.assertRaises(SchemaError):
            run_analyzer(analyzer, self.store, "source-a", "evidence")
        self.assert_empty()

    def test_candidate_cannot_replace_invocation_evidence(self) -> None:
        analyzer = FakeAnalyzer(candidate("other-source", "evidence"))
        with self.assertRaisesRegex(SchemaError, "evidence"):
            run_analyzer(analyzer, self.store, "source-a", "evidence")
        self.assert_empty()
