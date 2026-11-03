"""Versioned domain models for findings and proposals."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum
from pathlib import PurePosixPath

SCHEMA_VERSION = 1
MAX_EXCERPT_CHARS = 500
MAX_PROPOSAL_EVIDENCE = 5
MAX_SOURCE_HASH_CHARS = 128
MAX_STRUCTURED_TEXT_CHARS = 1000
MAX_RUN_DETAIL_CHARS = 500
MAX_COMPLETED_AT_CHARS = 100
MAX_RUN_OUTCOMES = 100


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


class SessionOutcomeStatus(StrEnum):
    """Privacy-safe result of processing one local session."""

    ANALYZED = "analyzed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class DailySessionOutcome:
    """Bounded derived metadata for one session, never transcript content."""

    session_hash: str
    status: SessionOutcomeStatus
    detail: str
    retryable: bool = False
    log_ref: str | None = None

@dataclass(frozen=True)
class EvidenceReference:
    """Bounded evidence derived from one source session."""

    source_hash: str
    excerpt: str


@dataclass(frozen=True)
class ProposalObservation:
    """One bounded observation contributing to proposal recurrence."""

    intent: str
    target: str
    scope: str
    evidence: EvidenceReference

    def __post_init__(self) -> None:
        """Reject empty identity fields and unbounded evidence."""
        for name in ("intent", "target", "scope"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise SchemaError(f"{name} must be a non-empty string")  # noqa: EM102, TRY003
        source_hash = self.evidence.source_hash
        excerpt = self.evidence.excerpt
        if (
            not isinstance(source_hash, str)
            or not source_hash.strip()
            or len(source_hash) > MAX_SOURCE_HASH_CHARS
        ):
            raise SchemaError("source_hash must contain at most 128 characters")  # noqa: EM101, TRY003
        if not isinstance(excerpt, str) or not excerpt.strip() or len(excerpt) > MAX_EXCERPT_CHARS:
            raise SchemaError("excerpt must contain at most 500 characters")  # noqa: EM101, TRY003

    @property
    def fingerprint(self) -> str:
        """Return a stable identity from normalized intent, target, and scope."""
        identity = "\0".join(
            " ".join(value.split()).casefold() for value in (self.intent, self.target, self.scope)
        )
        digest = hashlib.sha256(identity.encode(), usedforsecurity=False).hexdigest()
        return f"sha256:{digest}"


@dataclass(frozen=True)
class AnalyzerCandidate:
    """Validated structured analyzer output awaiting durable ingestion."""

    schema_version: int
    observation: ProposalObservation
    title: str
    rationale: str
    problem: str
    affected_workflow: str
    proposed_artifact: str
    expected_benefit: str
    risks: str
    validation: str

    def revision(self) -> ProposalRevision:
        """Build the initial reviewable revision without occurrence evidence."""
        return ProposalRevision(
            1,
            self.title,
            self.rationale,
            self.observation.target,
            (),
            self.problem,
            self.affected_workflow,
            self.proposed_artifact,
            self.expected_benefit,
            self.risks,
            self.observation.scope,
            self.validation,
        )


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


def _bounded_text(value: object, field: str) -> str:
    text = _text(value, field)
    if len(text) > MAX_STRUCTURED_TEXT_CHARS:
        raise SchemaError(f"{field} exceeds {MAX_STRUCTURED_TEXT_CHARS} characters")  # noqa: EM102, TRY003
    return text


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


def analyzer_candidate_from_mapping(value: object) -> AnalyzerCandidate:
    """Validate untrusted structured analyzer output before persistence."""
    root = _mapping(value, "candidate")
    version = _integer(root.get("schema_version"), "schema_version")
    if version != SCHEMA_VERSION:
        raise SchemaError(f"unsupported schema version: {version}")  # noqa: EM102, TRY003
    evidence = _mapping(root.get("evidence"), "evidence")
    observation = ProposalObservation(
        _bounded_text(root.get("intent"), "intent"),
        _bounded_text(root.get("target"), "target"),
        _bounded_text(root.get("scope"), "scope"),
        EvidenceReference(
            _text(evidence.get("source_hash"), "source_hash"),
            _text(evidence.get("excerpt"), "excerpt"),
        ),
    )
    fields = (
        "title",
        "rationale",
        "problem",
        "affected_workflow",
        "proposed_artifact",
        "expected_benefit",
        "risks",
        "validation",
    )
    return AnalyzerCandidate(
        version, observation, *(_bounded_text(root.get(name), name) for name in fields)
    )
