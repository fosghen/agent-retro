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
