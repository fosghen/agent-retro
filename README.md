# agent-retro

> **Compatibility: Claude Code and OpenAI Codex.** The extractor auto-detects both JSONL transcript formats.

A session retrospective skill for AI coding agents. Invoke `agent-retro` (or ask for a session retrospective) to analyze what happened, identify friction, and get concrete suggestions for improving your skills, rules, and workflows.

Follows the [Agent Skills](https://agentskills.io) open standard.

## What it does

`/agent-retro` reads your session transcript from disk and produces a structured analysis:

- **Full conversation arc** — every user message and assistant response, in order. No sampling, no skipping.
- **Token cost breakdown** — per-agent attribution so you can see where the budget went.
- **Tool result waste detection** — flags oversized tool results (a 45KB file read that was never used is money burned).
- **Friction analysis** — identifies user corrections, redirects, and abandoned approaches, then traces each to a root cause.
- **Actionable proposals** — specific edits to skills, rules, or config. Not vague "improve X" — the actual text to change.

The output is a markdown retro file plus an interactive walkthrough where you approve or defer each proposed action.

## Why this exists

Every agent framework has inline reflection (retry loops, critic agents). None of them do **post-session systemic reflection** — looking across an entire conversation to find patterns of failure and proposing configuration changes to prevent them next time.

This is the equivalent of an agile sprint retrospective, but for a single AI session, producing machine-editable artifacts rather than sticky notes on a board. See [references/design.md](references/design.md) for the full design rationale and comparison with Reflexion, LangGraph, CrewAI, and others.

## Install

**Recommended** (works with any Agent Skills-compatible tool):

```bash
npx skills add giannimassi/agent-retro
```

**Or clone manually** into your skills directory:

```bash
# Claude Code
git clone https://github.com/giannimassi/agent-retro.git ~/.claude/skills/agent-retro

# OpenAI Codex
git clone https://github.com/fosghen/agent-retro.git ~/.codex/skills/agent-retro
```

## Usage

At the end of any session, invoke the skill or ask:

```
Run a retrospective on this session.
```

The skill will:

1. Find your current session's transcript
2. Extract structured data (streaming, no full file load)
3. Analyze the conversation arc for friction patterns
4. Classify what the session produced
5. Propose concrete improvements
6. Walk you through each proposal for approval

### Daily Codex retrospective on macOS

Install the optional LaunchAgent from a local clone:

```bash
./scripts/install_launchd.sh
```

It runs at 09:00 local time and analyzes only the previous day's Codex sessions.
The background Codex process uses a read-only sandbox and writes its final
Markdown report to `~/.codex/worklog/retros/YYYY-MM-DD-daily.md`. Scheduler logs
stay local under `~/.codex/logs/`; session transcripts are never copied into the
repository.

### Extraction script standalone

The Python extraction script can be used independently:

```bash
# Quick session verification (reads only first/last 64KB)
python3 scripts/extract.py <session.jsonl> --metadata-only

# Compact extraction (tool counts, no individual calls)
python3 scripts/extract.py <session.jsonl> --summary

# Full extraction (includes every tool call detail)
python3 scripts/extract.py <session.jsonl>
```

## How it works

### Token-efficient extraction

The extraction script (`scripts/extract.py`) minimizes token usage:

- **Streaming** — processes JSONL line-by-line, never loads the full file into memory
- **No tool result content** — tracks result **sizes** without including the content. A 50MB session transcript produces ~30KB of extraction output.
- **Bounded metadata reads** — `--metadata-only` uses the file head/tail and streams only until the first real prompt when injected Codex instructions fill the head buffer.
- **Full conversation arc** — all user messages and assistant text are preserved. The arc is the whole point of a retro — you can't analyze friction you can't see.

### What the extraction captures

| Field | What | Why |
|---|---|---|
| `session` | ID, cwd, branch, duration | Context |
| `tokens` | Input/output/cache totals + USD cost | Budget analysis |
| `tools` | Call counts or full call list | Pattern detection |
| `agents` | Each dispatch with type, model, cost | Delegation efficiency |
| `skills` | Each invocation with args | Skill triggering analysis |
| `git` | Branches, commits, PR operations | What was shipped |
| `files` | Files read/written/edited | Scope tracking |
| `conversation_arc` | Full timeline of messages | Friction detection |
| `tool_result_sizes` | Per-tool total/avg/max bytes | Waste detection |

## Example output

See [examples/sample-retro.md](examples/sample-retro.md) for a retro from a real session.

## Roadmap

The analysis steps are agent-agnostic. Transcript readers currently support Claude Code and OpenAI Codex.
Version publication follows the capability gates in [docs/RELEASES.md](docs/RELEASES.md), not dates.

Planned support:

| Agent | Transcript format | Status |
|---|---|---|
| **Claude Code** | `~/.claude/projects/<cwd>/<session>.jsonl` | Supported |
| **Gemini CLI** | `~/.gemini/sessions/` | Planned |
| **OpenAI Codex** | `~/.codex/sessions/YYYY/MM/DD/*.jsonl` | Supported |
| **Cursor** | TBD | Planned |
| **Roo Code** | TBD | Planned |

Contributions welcome — if you know where another agent stores its session data, open an issue.

## Requirements

- Python 3.12 and `uv` for development and installation
- Tested transcript formats: Claude Code v2.1.59+ and current Codex rollout JSONL

Install the locked environment and verify the CLI:

```bash
uv sync --locked --all-groups
uv run agent-retro --help
```

## License

MIT
