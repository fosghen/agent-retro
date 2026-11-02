"""Versioned domain models for findings and proposals."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

SCHEMA_VERSION = 1


class SchemaError(ValueError):
    """Raised when persisted domain input violates the supported schema."""


class ProposalStatus(StrEnum):
    """Durable proposal lifecycle states."""

    NEW = "new"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    IMPLEMENTING = "implementing"
    IMPLEMENTED = "implemented"
    FAILED = "failed"


@dataclass(frozen=True)
class EvidenceReference:
    """Bounded evidence derived from one source session."""

    source_hash: str
    excerpt: str


@dataclass(frozen=True)
class Finding:
    """One validated analyzer observation."""

    schema_version: int
    kind: str
    summary: str
    evidence: tuple[EvidenceReference, ...]
