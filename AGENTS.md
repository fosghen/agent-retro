# Agent instructions

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

Before editing, reconcile the live PR chain through GitHub MCP. Keep reports
concise and distinguish observed results from assumptions or planned work.
