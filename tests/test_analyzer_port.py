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
