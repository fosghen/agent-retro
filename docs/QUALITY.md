# Quality policy and audit

Audit date: 2026-11-02, using repository configuration and clean-checkout checks.

## Current enforcement

- CI and pre-commit configuration run 140 unit tests.
- CI rejects over five commits per PR, over 50 changed lines, and binaries.
- GitHub Actions use commit-pinned official actions and read-only permissions.
- Compilation, shell/plist syntax, tests, and skill validation pass manually.

## Gaps observed

- No formatter, linter, typing, coverage, security, lock, or build gate exists.
- The local pre-commit hook is not installed, so its configuration is advisory.
- `main` has no branch protection or required status check; direct pushes and
  merges with failing or absent CI remain possible.
- GitHub permits unpinned third-party actions globally, although none exist now.
- CI tests only Python 3.12 while the README claims Python 3.8+ compatibility.

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
