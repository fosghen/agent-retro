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

For behavior changes, first add a focused failing test, implement the smallest
change, and then run the complete test suite. Keep extraction deterministic and
preserve compatibility with every documented agent format.

Work on a separate branch and deliver through a pull request. Never commit
directly to `main`. Each commit may contain at most 50 changed lines (additions
plus deletions), binary changes are forbidden, and each pull request may contain
at most 5 commits. Never bypass configured hooks with `--no-verify`.

Before editing, reconcile live pull request and issue state through the
GitHub REST API with `gh api`. Live GitHub state is authoritative over stale local refs
or prior reports. Treat commits, pushes, pull request mutations, merges, and
issue mutations as separate authorization boundaries. Keep reports concise and
distinguish observed results from assumptions or planned work.
