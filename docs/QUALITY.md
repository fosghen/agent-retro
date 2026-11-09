# Quality policy and audit

Audit date: 2026-11-09, using repository configuration, GitHub REST state, and
local configured checks.

<!-- quality-inventory
staged_hooks = ["change-limits", "agent-config", "scoped-ruff"]
pre_push_hooks = ["publication-readiness", "full-quality-gate"]
ci_steps = [
  "Check live issue state|python scripts/check_issue_state.py",
  "Check pull request process declaration|python scripts/check_pr_process.py",
  "Check pull request limits|python scripts/check_change_limits.py",
  "Run full quality gate|python scripts/run_quality_gate.py",
]
full_gate = [
  "python scripts/check_agent_config.py",
  "python -m scripts.check_quality_policy",
  "python scripts/check_shell_plist.py",
  "python scripts/check_package.py",
  "python scripts/check_ruff.py",
  "python -m scripts.check_puzzles",
  "python scripts/check_extractor_architecture.py",
  "pytest",
  "mypy --strict src/agent_retro scripts",
  "bandit -q -r src scripts",
  "pip-audit",
  "agent-retro --help",
  "python scripts/check_skill.py",
]
live_facts = "offline-audit-only"
temporary_suppressions = []
-->

## Current enforcement

- The shared gate checks agent metadata, shell and plist syntax, package build and
  clean installation, extractor architecture, repository-wide Ruff, pytest with branch coverage, strict
  mypy, Bandit, pip-audit, the installed CLI, and the skill contract.
- Pull-request CI rejects more than five commits, commits over 75 changed lines,
  pull requests over 250 changed lines, binary changes, branches without an issue
  reference, closed issue references, and contradictory risk declarations.
- CI installs the locked Python 3.12 environment and invokes the same shared gate
  used by the pre-push hook. The staged hook runs the faster change, agent-config,
  and Ruff checks.
- CI also runs the security checks every Monday at 05:23 UTC. GitHub Actions use
  commit-pinned actions and read-only repository permissions.
- The embedded inventory above is the checked source of truth for local tier
  ownership. `scripts.check_quality_policy` rejects drift without network access.
- Temporary suppressions must be registered in `temporary_suppressions` with a
  narrow scope, reason, and ISO review date. The full gate rejects incomplete or
  expired entries with their identity and deadline. No temporary suppression is
  currently active.

## Coverage policy

The protected gate measures line and branch coverage across the complete maintained
Python scope and enforces an 85% floor against the observed 87.01% baseline. A
repository-wide ratchet was selected over changed-line coverage because the parser,
storage, and migration paths are exercised across module boundaries; another diff
coverage owner would not replace that system evidence. Future increases require a
new measured baseline. Coverage remains supporting evidence, not a correctness goal.

## Foundation status

- Clean-checkout setup and hook bootstrap are delivered by
  [#110](https://github.com/fosghen/agent-retro/issues/110).
- The shared content gate delivered by #111 remains authoritative; Ruff and
  strict mypy delivered by #9 and #10 are blocking parts of that gate.
- The checked tier inventory and expiring suppression mechanism complete #112.

## Tier ownership

Staged hooks own fast branch, configuration, and formatting feedback. Pre-push
owns clean publication state and the complete local gate. CI invokes that same
gate and remains authoritative. These tiers complete the children of
[#13](https://github.com/fosghen/agent-retro/issues/13).

Suppressions must remain narrow and justified. New checks must fix causes rather
than weaken thresholds to hide existing violations.

## Repository enforcement

Live GitHub protection requires a current branch and the `quality` check, applies
to administrators, resolves conversations, and blocks force pushes and deletion.
Independent review remains opt-in and risk-based. Routine low-risk changes rely
on self-review plus protected deterministic CI; no workflow invokes a paid
reviewer. The PR declaration records provider, available model usage evidence,
and whether live external effects are absent, reversible administration, or
destructive/product-facing.

## Audit limitations

Repository files establish the local gate and CI inventory. GitHub REST establishes
the dated live branch-protection facts; those facts cannot be proven by an offline
content check and retain this dated audit procedure. macOS CI validates install,
repeat install, observable artifacts, and uninstall in a temporary HOME. It stubs
`launchctl`, so actual per-user service registration remains a real-system
boundary. pip-audit checks locked third-party
dependencies but skips the unpublished local `agent-retro` package.
