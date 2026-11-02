# Application architecture

## Goal

Turn local agent sessions into evidence-backed, user-controlled workflow
improvements without publishing transcripts or silently changing projects.

## Components

1. **Collector** discovers sessions for a bounded time window.
2. **Extractor** normalizes supported transcript formats into one schema.
3. **Analyzer** produces structured findings and candidate proposals.
4. **Proposal store** persists fingerprints, evidence, status, and history.
5. **Triage CLI** lets a user inspect, approve, reject, or defer proposals.
6. **Executor** converts an approved proposal into a branch and pull request.
7. **Evaluator** checks later sessions for evidence that the change helped.

## Data flow

`session paths -> normalized evidence -> findings -> deduplicated proposals ->
user decision -> implementation PR -> outcome observation`

Raw transcripts stay in their original local directories. Derived records must
contain bounded excerpts or hashes, never credentials or complete tool output.

## Proposal model

Every proposal has a stable fingerprint, type, title, rationale, evidence
references, occurrence count, confidence, target artifact, status, timestamps,
and an optional implementation PR. Status transitions are append-only events:
`new -> approved|rejected|deferred -> implementing -> implemented|failed`.

## Boundaries

- Analysis is read-only and may run unattended.
- Approval authorizes only the described proposal and target.
- Execution may create a branch and PR; it never merges automatically.
- The proposal store is local by default and contains no raw transcripts.
- GitHub access uses its REST API and least-privilege credentials.

## Initial technology
Use Python standard library plus SQLite for durable local state. Keep analysis
behind a port so the application can invoke Codex today and another engine
later. Keep deterministic discovery, normalization, deduplication, state
transitions, and GitHub request construction independently testable.

## Non-goals for the MVP

No web dashboard, multi-user server, cloud transcript storage, autonomous merge,
or automatic modification of arbitrary repositories.
