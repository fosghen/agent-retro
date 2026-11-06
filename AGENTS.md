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

Before editing, reconcile live pull request and issue state, the branch, and
remaining change budgets with
`uv run --frozen --no-sync python -m scripts.workflow_status`. It reads the
GitHub REST API through `gh`; live state is authoritative over stale local refs
or prior reports. Use `gh api` only when the compact status lacks required detail.

Development must follow this order:

1. Register an issue containing the outcome, acceptance criteria, scope, and
   known risk triggers.
2. Split it before implementation when one coherent commit cannot fit 50 lines,
   the work cannot fit one 250-line PR, or it contains independently deliverable
   high-risk components. Never manufacture a post-hoc split of one coherent diff.
3. Create a branch containing `issue-N`, matching the registered issue number.
4. Add focused failing tests, implement the smallest coherent change, and use
   focused checks while editing.
5. Self-review the complete diff. Independent review is not a routine quality
   gate and PR size alone is never a reason to request it.
6. Create the logical commits, then run `uv run --frozen --no-sync python -m
   scripts.workflow_status --publication` on the clean branch.
7. Push once. The installed pre-push hook runs the complete content quality gate;
   do not run that gate manually as well. If the hook is unavailable, run the
   gate manually once and keep the missing-hook limitation visible.
8. Publish one focused PR whose `Closes #N` matches the branch issue.

Use independent review only when the PR changes persisted schemas or migrations,
concurrency or transaction boundaries, privacy/security/authentication/
authorization, destructive or external side effects, or when concrete
correctness uncertainty remains after self-review. Declare the trigger in the PR.

Never commit directly to `main`. Each logical commit may contain at most 50
changed lines, each PR at most 250 changed lines and 5 commits, and binary changes
are forbidden. Never split coherent code solely to approach a line limit, and
never bypass configured hooks with `--no-verify`.

Treat commits, pushes, pull request mutations, merges, and issue mutations as
separate authorization boundaries. Keep reports concise and distinguish observed
results from assumptions or planned work.

## Delivery telemetry

Agent-authored issue work must use
[`agent-delivery-telemetry`](https://github.com/fosghen/agent-delivery-telemetry#readme).
Run `begin` after `workflow_status` and before editing. Route each controlled
non-interactive `codex exec --json` run through `capture-codex-usage`; never
retain its raw event stream. After the exact head passes the quality gate, run
`finish`, bind every captured run, and publish the owned `adt:v1` comment to the
pull request. Run `report` after merge.

Telemetry does not replace issue-first, TDD, review judgment, or required gates.
Never invent exact token usage for an interactive or uninstrumented run; preserve
it as unavailable. The tool README is the canonical command reference.
