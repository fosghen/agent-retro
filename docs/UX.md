# User experience

## Product promise

Agent Retro finds recurring friction, explains why an improvement is worth making, and waits for an explicit decision before changing anything.

## Daily experience

The scheduled run creates a short digest, not a long transcript summary:

- sessions analyzed and sessions skipped with reasons;
- new proposals that crossed the recurrence threshold;
- existing proposals with stronger or contradictory evidence;
- failed analysis steps that need attention;
- a pointer to the local proposal queue.

## Triage experience

The first interface is a CLI:

```text
agent-retro list [--status new]
agent-retro show <proposal-id>
agent-retro approve <proposal-id>
agent-retro reject <proposal-id> --reason <text>
agent-retro defer <proposal-id> --until <date>
agent-retro implement <proposal-id>
```

`show` presents the problem, evidence, affected workflow, proposed artifact,
expected benefit, risks, scope, and validation without full transcript dumps.

## Decision semantics

Approval freezes the reviewed revision; new evidence creates another revision.
Rejection suppresses equivalents until evidence changes; deferral has a date.

## Implementation experience

`implement` previews scope and effects, then creates a branch and pull request.
It stops on ownership ambiguity, missing authority, failed tests, or scope drift.

## Failure experience

Failures identify the stage, preserve state, show a safe retry, and never report
partial work as implemented. Background failures appear in the next digest.

## MVP success criteria

A user can decide a proposal in two minutes, trace its evidence, and implement an approved change without copying prompts.
