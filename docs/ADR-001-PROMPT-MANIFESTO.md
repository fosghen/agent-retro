# ADR 001: Adopt the prompt manifesto selectively

Status: accepted

## Context

The `yegor256/prompt` manifesto was reviewed at commit
`4fb8a3f125b3481de01d489a170f56db29a83694`. It mixes portable delivery
discipline with Java-oriented object rules and personal prose preferences.
Copying it wholesale would conflict with Agent Retro's Python codebase and
would duplicate existing repository policy.

## Decision

| Area | Decision | Reason |
| --- | --- | --- |
| Scope control | Accept | Minimal, issue-backed changes match `AGENTS.md` and the enforced change limits. |
| TDD | Accept | Focused red/green tests are already required for behavior changes. |
| Puzzle Driven Development | Adapt | Deferred debt must link an issue; the puzzle gate already enforces this mechanically. |
| Quality gates | Accept | Violations should be fixed, not suppressed; pre-commit and CI own enforcement. |
| Tests | Adapt | Short deterministic tests and bounded waits are useful; one assertion, mocks bans, and unusual spelling are not universal quality signals. |
| Object rules | Reject | Immutable values and composition help, but bans on static methods, getters, utility modules, reflection, and names ending in `-er` do not fit Python or this product. |
| Prose rules | Adapt | Plain, concise prose and contextual one-sentence errors help; bracket and indentation doctrines belong to formatters, not prompts. |

Top-down design, fail-fast validation, offline tests, immutable domain values,
and explicit timeouts remain engineering guidance. Aesthetics never outrank
correctness, user outcomes, privacy, or recoverability.

## Duplication audit

- `AGENTS.md` already owns scope, TDD, sensitive fixtures, branches, commits,
  pull requests, and non-bypassable hooks.
- `docs/QUALITY.md` owns deterministic gates, suppression policy, and protected
  branch expectations.
- `SKILL.md` owns retrospective behavior and action specificity; it should not
  become a second repository-development policy.
- Issue #228 supplied the mechanical issue-backed puzzle check. Issue #60 is the
  existing place to reconsider broader prose and agent-guidance linting.
