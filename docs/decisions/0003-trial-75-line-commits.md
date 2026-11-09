# ADR 0003: Trial 75-line logical commits

- Status: accepted
- Date: 2026-11-09
- Issue: #230
- Implementation: #243

## Evidence

The 40 most recent merged pull requests have a 99-line median and 191-line
90th percentile; 15 reached the five-commit ceiling. Median commit count is four.
PR-open-to-merge time has a 38-second median, but that clock starts after the
implementation, so it is not issue-to-merge lead time.

ADT traces for #237-#242 report 97-442 seconds of delivery lead time and
68-411 seconds of active time. Exact tokens are unavailable for every interactive
trace. ADT also reports zero rework for #242 even though its first pre-push gate
failed, so current rework and token evidence cannot select a limit.

The recent small changes show both useful and mechanical splitting. PR #237
separated the enforced inventory from remaining gaps; #238 separated the gate
from its rationale; and #239 separated policy from its README link. Those are
coherent commits. PR #242 used five commits of 46, 21, 36, 41, and 47 lines, and
a coherent 60-line staged slice was rejected before being mechanically divided.
No observed defect can be attributed to a commit exceeding 50 lines.

## Options

- **50 lines:** strongest size pressure, but demonstrated mechanical splitting.
- **75 lines:** admits the observed 60-line slice while retaining a hard bound.
- **100 lines:** reduces friction further, but doubles the untested current cap.
- **No commit cap:** leaves only the 250-line PR bound and permits monolithic PRs.

## Decision

Trial a 75-line per-commit maximum through #243. Keep the 250-line PR maximum,
five-commit maximum, binary rejection, issue linkage, and full gate unchanged.
After 20 merged PRs, compare ceiling hits, failed gates, human intervention,
issue-to-merge time, and exact token evidence where available. Keep 75 unless the
trial shows worse reviewability or defects; change it only through another
evidence-backed decision. Commit size never triggers independent review by itself.

## Limitations

The sample is one repository under one primary operator, recent PRs are selected
after the policy already shaped them, and current telemetry lacks exact tokens and
truthful failed-verification rework. This decision is a bounded experiment, not a
claim that 75 lines is universally optimal.
