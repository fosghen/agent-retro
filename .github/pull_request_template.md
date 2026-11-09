## Outcome

<!-- State the user-visible result and the issue closed by this PR. -->

Closes #ISSUE

## Verification

<!-- List focused tests and the single full gate: python scripts/run_quality_gate.py -->

## Risk declaration

Risk: low
Independent review: not-used
Review provider: none
Model review usage: not-applicable
External effects: none

High-risk triggers:

- [ ] data migration or persisted-schema change
- [ ] concurrency, locking, or transaction-boundary change
- [ ] privacy, security, authentication, or authorization change
- [ ] destructive operation or external side effect
- [ ] unresolved correctness uncertainty after self-review
- [ ] explicit user request for independent review

<!-- Low risk requires no checked triggers and no independent review.
High risk requires Risk: high, at least one checked trigger, and
Independent review: completed with provider human or model. PR size alone is
not a trigger. External effects are none, reversible-administration, or
destructive-or-product-facing. For model review, replace usage with unavailable
or `tokens=N; cost=USD N`; never estimate missing evidence. -->
