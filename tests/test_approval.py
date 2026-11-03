import sqlite3
import tempfile
import unittest
from pathlib import Path

from agent_retro.cli import main
from agent_retro.models import (
    EvidenceReference,
    ProposalObservation,
    ProposalStatus,
    SchemaError,
    StatusEvent,
)
from agent_retro.store import ProposalStore


def observation(source_hash: str) -> ProposalObservation:
    return ProposalObservation(
        "Improve review", "agent-retro", "one skill", EvidenceReference(source_hash, "bounded")
    )
