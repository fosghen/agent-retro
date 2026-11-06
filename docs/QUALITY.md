# Quality policy and audit

Audit date: 2026-11-02, using repository configuration, GitHub REST state, and
local configured checks.

## Current enforcement

- Pull-request CI rejects more than five commits, commits over 50 changed lines,
  binary changes, and changes made directly on a protected branch name.
- CI installs the locked Python 3.12 development environment, runs pytest with
  branch coverage and a 67% minimum, scans source with Bandit, audits locked
  dependencies with pip-audit, and smoke-tests the installed CLI.
- The pre-commit configuration runs the same change-policy, pytest, Bandit, and
  pip-audit commands. Hook installation is not automated or verified yet.
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
2. strict mypy across application and deterministic scripts ([#10](https://github.com/fosghen/agent-retro/issues/10));
3. shell and plist syntax, package build, clean-environment install, and official
   skill validation.

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
