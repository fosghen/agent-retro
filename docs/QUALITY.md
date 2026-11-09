# Quality policy and audit

Audit date: 2026-11-09, using repository configuration, GitHub REST state, and
local configured checks.

## Current enforcement

- The shared gate checks agent metadata, shell and plist syntax, package build and
  clean installation, repository-wide Ruff, pytest with branch coverage, strict
  mypy, Bandit, pip-audit, the installed CLI, and the skill contract.
- Pull-request CI rejects more than five commits, commits over 75 changed lines,
  pull requests over 250 changed lines, binary changes, branches without an issue
  reference, closed issue references, and contradictory risk declarations.
- CI installs the locked Python 3.12 environment and invokes the same shared gate
  used by the pre-push hook. The staged hook runs the faster change, agent-config,
  and Ruff checks.
- CI also runs the security checks every Monday at 05:23 UTC. GitHub Actions use
  commit-pinned actions and read-only repository permissions.

## Coverage policy

The protected gate measures line and branch coverage across the complete maintained
Python scope and enforces an 85% floor against the observed 87.01% baseline. A
repository-wide ratchet was selected over changed-line coverage because the parser,
storage, and migration paths are exercised across module boundaries; another diff
coverage owner would not replace that system evidence. Future increases require a
new measured baseline. Coverage remains supporting evidence, not a correctness goal.

## Gaps observed

- The clean-checkout setup and hook bootstrap remain tracked by
  [#110](https://github.com/fosghen/agent-retro/issues/110).
- Explicit quality tiers and expiring suppressions remain tracked by
  [#112](https://github.com/fosghen/agent-retro/issues/112).
- The shared content gate delivered by #111 is complete; Ruff and strict mypy
  delivered by #9 and #10 are blocking parts of that gate.

## Remaining target gate

The remaining children of [#13](https://github.com/fosghen/agent-retro/issues/13)
are #110 and #112. The authoritative full command already exists and CI invokes
it; setup and tier ownership remain incomplete until those children close.

Suppressions must remain narrow and justified. New checks must fix causes rather
than weaken thresholds to hide existing violations.

## Repository enforcement

Live GitHub protection requires a current branch and the `quality` check, applies
to administrators, resolves conversations, and blocks force pushes and deletion.
Independent review remains risk-based rather than universally required.

## Audit limitations

Repository files establish the local gate and CI inventory. GitHub REST establishes
the dated live branch-protection facts; those facts cannot be proven by an offline
content check. The audit did not repeat setup from a clean checkout or validate the
macOS LaunchAgent lifecycle in hosted CI. pip-audit checks locked third-party
dependencies but skips the unpublished local `agent-retro` package.
