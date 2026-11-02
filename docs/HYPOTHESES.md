# Product hypotheses

These are falsifiable assumptions measured locally without transcript uploads.

## H1: recurrence filtering improves relevance

If proposals appear only after two materially similar observations, fewer than
30% will be rejected as noise during a four-week personal trial. Compare this
with single-occurrence candidates kept in a hidden control set. If rejection is
higher, improve fingerprints or require three occurrences.

## H2: a quiet digest earns attention

If the digest reports only changed proposal state, it will be opened on at least
60% of working days and take under three minutes to process. If not, reduce its
frequency or move delivery into the user's existing daily workflow.

## H3: evidence makes decisions fast

A proposal with bounded evidence, affected workflow, expected benefit, scope,
and validation can be approved, rejected, or deferred in under two minutes for
80% of cases. Time and abandoned decisions test this; redesign `show` if missed.

## H4: approval-to-PR removes mechanical work

For supported skill and repository-rule updates, at least 70% of approved
proposals should reach a valid PR without manual prompt copying. Failures are
classified as missing data, unsupported scope, quality gate, or authorization.

## H5: changes measurably reduce recurrence

Within ten comparable sessions after implementation, at least half of evaluated
proposals should show lower recurrence without a related regression. Otherwise
the analyzer is optimizing symptoms rather than workflows.

## H6: local-first handling is sufficient

Users should complete the workflow without storing raw transcripts off-machine.
Any required upload blocks the feature pending explicit retention controls.

## H7: automation cost remains bounded

A daily run should inspect only the target window, reuse deterministic extraction,
and keep model work proportional to meaningful sessions. Track session count,
input size, duration, and failures; introduce hard budgets before team use.

## Review cadence

Review after the first end-to-end trial and monthly thereafter. Record decisions
beside each hypothesis; never rewrite thresholds after observing outcomes.
