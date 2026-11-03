"""Bounded analyzer port and orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from agent_retro.models import (
    MAX_EXCERPT_CHARS,
    MAX_SOURCE_HASH_CHARS,
    AnalyzerCandidate,
    EvidenceReference,
    Proposal,
    SchemaError,
    analyzer_candidate_from_mapping,
)

if TYPE_CHECKING:
    from agent_retro.store import ProposalStore


@dataclass(frozen=True)
class AnalyzerInput:
    """Normalized, bounded evidence supplied to an analyzer."""

    source_hash: str
    excerpt: str

    def __post_init__(self) -> None:
        """Reject inputs that bypass the bounded-input factory."""
        if not isinstance(self.source_hash, str) or not isinstance(self.excerpt, str):
            raise SchemaError("analyzer input must contain strings")  # noqa: EM101, TRY003
        normalized_hash = " ".join(self.source_hash.split())
        normalized_excerpt = " ".join(self.excerpt.split())
        if (
            not normalized_hash
            or normalized_hash != self.source_hash
            or len(normalized_hash) > MAX_SOURCE_HASH_CHARS
        ):
            raise SchemaError("invalid analyzer source hash")  # noqa: EM101, TRY003
        if (
            not normalized_excerpt
            or normalized_excerpt != self.excerpt
            or len(normalized_excerpt) > MAX_EXCERPT_CHARS
        ):
            raise SchemaError("invalid analyzer excerpt")  # noqa: EM101, TRY003


class Analyzer(Protocol):
    """Port implemented by structured-output analyzer adapters."""

    def analyze(self, value: AnalyzerInput, /) -> object:
        """Return untrusted structured output for deterministic validation."""
        ...


def normalize_input(source_hash: str, excerpt: str) -> AnalyzerInput:
    """Normalize and bound evidence before any analyzer invocation."""
    normalized_hash = " ".join(source_hash.split())
    normalized_excerpt = " ".join(excerpt.split())[:MAX_EXCERPT_CHARS]
    return AnalyzerInput(normalized_hash, normalized_excerpt)


def invoke_analyzer(analyzer: Analyzer, value: AnalyzerInput) -> object:
    """Invoke the external analyzer without validating or persisting output."""
    return analyzer.analyze(value)


def validate_output(value: object, source: AnalyzerInput) -> AnalyzerCandidate:
    """Validate output and bind it to the evidence supplied for invocation."""
    candidate = analyzer_candidate_from_mapping(value)
    if candidate.observation.evidence != EvidenceReference(source.source_hash, source.excerpt):
        raise SchemaError("candidate evidence differs from analyzer input")  # noqa: EM101, TRY003
    return candidate


def persist_candidate(
    store: ProposalStore, candidate: AnalyzerCandidate, *, occurred_at: str | None = None
) -> Proposal | None:
    """Persist one already validated candidate through recurrence aggregation."""
    return store.ingest_candidate(candidate, occurred_at=occurred_at)
