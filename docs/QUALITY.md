# Quality policy and audit

Audit date: 2026-11-02, using repository configuration and clean-checkout checks.

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
- Strict mypy is not enforced ([#10](https://github.com/fosghen/agent-retro/issues/10)).
- There is no single local gate or verified hook bootstrap
  ([#13](https://github.com/fosghen/agent-retro/issues/13)).
- `main` has no branch protection or required `quality` status check
  ([#14](https://github.com/fosghen/agent-retro/issues/14)).
- Agent configuration lacks structural validation
  ([#46](https://github.com/fosghen/agent-retro/issues/46)).

## Target gate

One reproducible command must run the same blocking checks locally and in CI:

1. repository change policy and generated-file policy;
2. Ruff format and lint with an explicit strict rule set;
3. mypy strict over application and deterministic scripts;
4. pytest with branch coverage and a ratcheted minimum;
5. Bandit and dependency vulnerability scanning;
6. shell syntax, plist lint, and official skill validation;
7. package build, clean-environment install, and CLI smoke test.

Suppressions need narrow scope, a reason, and preferably an issue. Checks may be
incremental but must not be weakened merely to hide existing violations.

The CI security gate also runs every Monday at 05:23 UTC so newly disclosed
dependency vulnerabilities are detected even when the repository is idle.

## Repository enforcement

Protect `main`, require current branches and quality CI, block force pushes and
deletion, and include admins. Keep review optional, while requiring approval before
the application creates an implementation PR.

## Compatibility decision required

Test every declared Python version or raise the minimum. Python 3.12 is recommended
because execution and CI use it; preserving 3.8 needs a compatibility matrix.

## Audit limitations

No dependency or security checker ran because none is declared. Branch rules came
from GitHub REST API; organization-level rulesets were not assumed.
