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
