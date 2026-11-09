# Quality policy and audit

Audit date: 2026-11-09, using repository configuration, GitHub REST state, and
local configured checks.

## Current enforcement

- The shared gate checks agent metadata, shell and plist syntax, package build and
  clean installation, repository-wide Ruff, pytest with branch coverage, strict
  mypy, Bandit, pip-audit, the installed CLI, and the skill contract.
- Pull-request CI rejects more than five commits, commits over 50 changed lines,
  pull requests over 250 changed lines, binary changes, branches without an issue
  reference, closed issue references, and contradictory risk declarations.
- CI installs the locked Python 3.12 environment and invokes the same shared gate
  used by the pre-push hook. The staged hook runs the faster change, agent-config,
  and Ruff checks.
- CI also runs the security checks every Monday at 05:23 UTC. GitHub Actions use
  commit-pinned actions and read-only repository permissions.

## Gaps observed

- Ruff formatting and linting are not enforced ([#9](https://github.com/fosghen/agent-retro/issues/9)).
- Strict mypy covers the application and deterministic scripts through the shared
  publication gate used by pre-push and CI.
- There is no single local gate or verified hook bootstrap
  ([#13](https://github.com/fosghen/agent-retro/issues/13)).
- `main` has no branch protection or required `quality` status check
  ([#14](https://github.com/fosghen/agent-retro/issues/14)).

## Remaining target gate

The complete gate tracked by [#13](https://github.com/fosghen/agent-retro/issues/13)
must expose one setup command and one local command that CI also uses. Remaining
work includes:

1. Ruff format and lint ([#9](https://github.com/fosghen/agent-retro/issues/9));
2. strict mypy across application and deterministic scripts ([#10](https://github.com/fosghen/agent-retro/issues/10)).

Suppressions must remain narrow and justified. New checks must fix causes rather
than weaken thresholds to hide existing violations.

## Repository enforcement

Planned under [#14](https://github.com/fosghen/agent-retro/issues/14): protect
`main`, require current branches and the `quality` check, block force pushes and
deletion, and apply the rules to administrators. Review remains optional.

## Audit limitations

This audit inspected repository configuration at the dated `main` revision and
ran the configured checks on macOS. It did not repeat setup from a clean checkout
or validate Linux-specific behavior. GitHub REST reported that `main` was
unprotected; organization-level rulesets were not assumed. pip-audit checks locked
third-party dependencies but skips the unpublished local `agent-retro` package.
