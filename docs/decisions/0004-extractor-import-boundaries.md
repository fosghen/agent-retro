# ADR 0004: Enforce extractor imports with a repository-owned AST gate

Status: accepted

## Context

The former monolithic extractor now exposes a compatibility entry point in
`scripts/extract.py` and typed implementation modules under
`agent_retro.transcript_*`. The split is useful only if imports continue to
follow the streaming data flow instead of recreating cycles or reaching through
the entry point.

## Components and public interfaces

1. `transcript_io` owns raw JSONL input, format detection, and `JSONRecord`.
2. `transcript_metadata` owns bounded metadata parsing and may use `io`.
3. `transcript_normalize` converts raw provider records and may use `io`.
4. `transcript_session`, `transcript_conversation`, `transcript_tools`, and
   `transcript_aggregate` are independent projections over normalized records.
5. `transcript_stream` composes those projections into `StreamState`.
6. `transcript_subagents` may reuse normalization and aggregation.
7. `transcript_result.extract_transcript` is the typed composition root.
8. `scripts/extract.py` is a compatibility CLI and may import only public typed
   modules; package modules must never import it.

The public boundary is the functions imported by `transcript_result` plus
`extract_transcript`. Callers should not depend on private underscore-prefixed
helpers in another component.

## Allowed dependency direction

`io -> metadata|normalize -> projections -> stream -> result -> CLI`

`subagents` is a side input to `result` and may depend on `normalize`,
`aggregate`, and `metadata`. Projection modules may share `JSONRecord` as a
type-only import but must not depend on `stream`, `result`, `subagents`, or the
CLI. No `transcript_*` module may form an import cycle.

## Options considered

- **Import Linter:** mature Python import-graph contracts with forbidden,
  layered, independence, and cycle rules. It adds a runtime development
  dependency and its generic diagnostics do not express this repository's
  corrective module direction without several overlapping contracts.
- **Easement:** explicit components, evidence coverage, baselines, and rich CI
  formats across multiple languages. This repository is Python-only, so its
  external binary plus SCIP/indexer lifecycle is disproportionate today.
- **Repository-owned AST gate:** Python's standard `ast` module is sufficient
  for the small, static package. It adds no dependency and can name the violated
  boundary and the permitted direction. It will not attempt dynamic import
  resolution or third-party dependency analysis.

## Decision

Use a small repository-owned AST gate for extractor imports. Run it from the
existing aggregate quality command and CI. Reconsider Import Linter when the
package has multiple architectural domains or transitive contracts; reconsider
Easement if Agent Retro becomes a polyglot repository.

## Fixture contract

Positive fixtures contain an allowed lower-to-higher import and a type-only
`JSONRecord` import. Negative fixtures cover a projection importing `result`, a
package module importing `scripts.extract`, and a two-module cycle. Each failure
must name the source module, forbidden target, boundary, and corrective allowed
direction. The live package is checked in addition to fixtures, so the initial
baseline is zero accepted violations.
