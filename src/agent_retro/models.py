"""Versioned domain models for findings and proposals."""

from __future__ import annotations

from dataclasses import dataclass, replace
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


@dataclass(frozen=True)
class ProposalRevision:
    """Immutable user-reviewable proposal content."""

    number: int
    title: str
    rationale: str
    target: str
    evidence: tuple[EvidenceReference, ...]


_TRANSITIONS = {
    ProposalStatus.NEW: {ProposalStatus.APPROVED, ProposalStatus.REJECTED, ProposalStatus.DEFERRED},
    ProposalStatus.DEFERRED: {ProposalStatus.APPROVED, ProposalStatus.REJECTED},
    ProposalStatus.APPROVED: {ProposalStatus.IMPLEMENTING},
    ProposalStatus.IMPLEMENTING: {ProposalStatus.IMPLEMENTED, ProposalStatus.FAILED},
}


@dataclass(frozen=True)
class Proposal:
    """Current proposal state and immutable revision."""

    schema_version: int
    fingerprint: str
    status: ProposalStatus
    revision: ProposalRevision

    def transition(self, target: ProposalStatus) -> Proposal:
        """Return a proposal in the target state when the transition is valid."""
        if target not in _TRANSITIONS.get(self.status, set()):
            message = f"invalid status transition: {self.status} -> {target}"
            raise SchemaError(message)
        return replace(self, status=target)


@dataclass(frozen=True)
class StatusEvent:
    """Append-only record of a proposal status transition."""

    schema_version: int
    fingerprint: str
    previous: ProposalStatus
    current: ProposalStatus
    occurred_at: str
