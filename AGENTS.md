# Agent instructions

## Project overview

Agent Retro is a Python 3.12 local-first Codex retrospective application and
distributable skill.

## Setup and checks

Set up with `uv sync --locked --all-groups`. Run tests with
`uv run --frozen --no-sync pytest` and validate agent configuration with
`uv run --frozen --no-sync python scripts/check_agent_config.py`.

Read `README.md`, `SKILL.md`, and relevant tests before changing behavior. Treat
session logs as sensitive input: never commit real transcripts, credentials, or
private source. Use synthetic fixtures only.

## Development state machine

Before editing, reconcile live pull request and issue state through the
GitHub REST API with `gh api`. Live GitHub state is
authoritative over stale local refs or prior reports.

Development must follow this order:

1. Register an issue containing the outcome, acceptance criteria, scope, and
   known risk triggers.
2. Split it before implementation when the work cannot fit one 250-line PR or
   contains independently deliverable high-risk components.
3. Create a branch containing `issue-N`, matching the registered issue number.
4. Add focused failing tests, implement the smallest coherent change, and use
   focused checks while editing.
5. Self-review the complete diff. Independent review is not a routine quality
   gate and PR size alone is never a reason to request it.
6. Run `uv run --frozen --no-sync python scripts/run_quality_gate.py` once after
   the diff is stable. Repeat it only when code changes after that successful run.
7. Publish one focused PR whose `Closes #N` matches the branch issue.

Use independent review only when the PR changes persisted schemas or migrations,
concurrency or transaction boundaries, privacy/security/authentication/
authorization, destructive or external side effects, or when concrete
correctness uncertainty remains after self-review. Declare the trigger in the PR.

Never commit directly to `main`. Each logical commit may contain at most 100
changed lines, each PR at most 250 changed lines and 5 commits, and binary changes
are forbidden. Never split coherent code solely to approach a line limit, and
never bypass configured hooks with `--no-verify`.

Treat commits, pushes, pull request mutations, merges, and issue mutations as
separate authorization boundaries. Keep reports concise and distinguish observed
results from assumptions or planned work.
