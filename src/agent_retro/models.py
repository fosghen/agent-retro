"""Versioned domain models for findings and proposals."""

from __future__ import annotations

from collections.abc import Mapping
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
    problem: str = "Not recorded"
    affected_workflow: str = "Not recorded"
    proposed_artifact: str = "Not recorded"
    expected_benefit: str = "Not recorded"
    risks: str = "Not recorded"
    scope: str = "Not recorded"
    validation: str = "Not recorded"


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


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaError(f"{field} must be an object")  # noqa: EM102, TRY003
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{field} must be a non-empty string")  # noqa: EM102, TRY003
    return value


def _integer(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise SchemaError(f"{field} must be a positive integer")  # noqa: EM102, TRY003
    return value


def proposal_from_mapping(value: object) -> Proposal:
    """Validate untrusted structured data and build a typed proposal."""
    root = _mapping(value, "proposal")
    version = _integer(root.get("schema_version"), "schema_version")
    if version != SCHEMA_VERSION:
        raise SchemaError(f"unsupported schema version: {version}")  # noqa: EM102, TRY003
    try:
        status = ProposalStatus(_text(root.get("status"), "status"))
    except ValueError as error:
        raise SchemaError("status is unknown") from error  # noqa: EM101, TRY003
    raw_revision = _mapping(root.get("revision"), "revision")
    raw_evidence = raw_revision.get("evidence")
    if not isinstance(raw_evidence, list):
        raise SchemaError("evidence must be a list")  # noqa: EM101, TRY003
    evidence = tuple(
        EvidenceReference(
            _text(_mapping(item, "evidence item").get("source_hash"), "source_hash"),
            _text(_mapping(item, "evidence item").get("excerpt"), "excerpt"),
        )
        for item in raw_evidence
    )
    revision = ProposalRevision(
        _integer(raw_revision.get("number"), "revision number"),
        _text(raw_revision.get("title"), "title"),
        _text(raw_revision.get("rationale"), "rationale"),
        _text(raw_revision.get("target"), "target"),
        evidence,
        *(
            _text(raw_revision.get(field, "Not recorded"), field)
            for field in (
                "problem",
                "affected_workflow",
                "proposed_artifact",
                "expected_benefit",
                "risks",
                "scope",
                "validation",
            )
        ),
    )
    return Proposal(version, _text(root.get("fingerprint"), "fingerprint"), status, revision)
