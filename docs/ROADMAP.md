# Product roadmap

Items are dependency-ordered and delivered through small issues and PRs.

## Phase 0: trustworthy foundation

- Enforce formatting, linting, strict typing, coverage, and security checks.
- Protect `main`, require CI, install hooks, and package a reproducible CLI.
- Document data retention, redaction, upgrade, and recovery behavior.

Exit: a clean checkout can run one documented gate matching protected CI.

## Phase 1: structured proposals

- Define versioned schemas and a SQLite store with atomic migrations and events.
- Fingerprint equivalent proposals and aggregate recurrence across sessions.
- Emit structured analyzer output and validate it before persistence.

Exit: repeated evidence creates one durable proposal with occurrence history.

## Phase 2: human triage

- Implement triage commands with frozen approvals, rejection reasons, and dates.
- Produce a quiet daily digest containing only meaningful state changes.

Exit: every proposal has an auditable user decision and no silent scope change.

## Phase 3: controlled implementation

- Map proposal types to skills and preview repositories, checks, and effects.
- Create a branch and PR through GitHub REST API after explicit approval.
- Persist implementation attempts, failures, checks, and the resulting PR.

Exit: one approved skill update can become a tested PR without manual copying.

## Phase 4: outcome evaluation

- Link later evidence and classify outcomes by changed recurrence rates.
- Surface stale rules, rejected recurring needs, and false-positive analyzers.

Exit: the application can demonstrate whether an implemented change helped.

## Later exploration

Add team queues, notifications, and web UI only after validating local use.

## Release policy

Versions are released only when their capability milestone and common gate are
complete. See [RELEASES.md](RELEASES.md) for the `v0.2.0` through `v1.0.0` gates.
