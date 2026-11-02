# Milestone-gated releases

Releases follow completed capabilities, never dates; delays do not lower gates.

## Common release gate

Every version requires:

- all milestone issues closed or explicitly moved with a recorded rationale;
- protected required CI green on the exact `main` commit being tagged;
- locked clean install, package build, and installed CLI smoke test;
- current user, migration, recovery, privacy, and security documentation;
- a realistic local acceptance run with failures and skipped checks visible;
- no unresolved critical data-loss, credential, privacy, or security finding.

The Git tag and GitHub Release define a published version. A version string on
unreleased `main` is not itself a release. Pre-releases may gather evidence but
do not satisfy the stable release gate.

## `v0.2.0`: Foundation

Complete the Foundation milestone: strict Ruff and mypy, branch coverage,
security scanning, one local/CI gate, protected `main`, retention policy, and a
supported install and upgrade workflow. This is the first technical release of
the reliable retrospective tool.

## `v0.3.0`: Proposal loop MVP

Complete Proposal loop: versioned models, SQLite persistence and migrations,
deduplication, validated analyzer output, triage decisions, and a change-only
daily digest. This is the first release of Agent Retro as an application.

## `v0.4.0`: Controlled implementation

Complete Controlled implementation: read-only scope preview, durable execution
attempts, approved skill updates, and GitHub pull-request publication. Execution
requires the frozen approved revision and never merges its own pull request.

## `v1.0.0`: Outcome evaluation

Complete Outcome evaluation: later evidence classifies impact, hypothesis
metrics are durable, and daily analysis has enforced workload budgets. Before
`v1.0.0`, demonstrate at least three complete proposal-to-evaluation cycles and
verify upgrade, migration, backup, and recovery paths without manual repair.

## Scope changes

Moving an issue between release milestones is a product decision recorded on the
issue and milestone. A release cannot silently omit a failed acceptance check;
it either waits, publishes an explicit pre-release, or changes scope visibly.
