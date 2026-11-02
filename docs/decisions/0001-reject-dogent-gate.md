# ADR 0001: Reject dogent as a repository gate

Status: accepted on 2026-11-02.

## Context

Dogent 0.13.3 is an opinionated prose linter for `AGENTS.md` and `SKILL.md`.
The repository already uses agnix 0.60.3 for structural Codex validation. This
study asks whether dogent adds enough reliable signal to justify another gate.

## Method

Run the pinned deterministic scanner from a clean `main` checkout:

```bash
npm_config_cache=/tmp/agent-retro-npm-cache \
  npx --yes @yegor256/dogent@0.13.3 --offline AGENTS.md SKILL.md
```

The offline run reported 487 findings across 30 rules. Classify a finding as
useful only when applying it would improve correctness, safety, or durable
readability without contradicting the maintained product contract. Treat
mechanical house style as low-value rather than useful.

Results:

- 10 useful findings (2.1%): missing fence languages, selected undefined
  acronyms, one volatile price threshold, and a valid progressive-disclosure
  concern about the long skill entrypoint.
- 364 conflicting findings (74.7%): rules that reject supported metadata,
  Markdown hierarchy, articles, wrapped prose, or non-imperative explanation.
- 113 false-positive or low-value findings (23.2%).
- Three findings overlap agnix scope: frontmatter, instruction budget, and skill
  length. The frontmatter verdict conflicts with agnix and official guidance.

The model-backed oracle was not evaluated. It is nondeterministic, needs an API
or local model, and dogent already reports its token usage and estimated cost.
Observed model cost for this study is therefore $0.

## Decision

Reject dogent as a dependency, pre-commit hook, or CI gate. Keep agnix as the
structural validator and address the ten useful observations through focused
changes or behavioral evidence. Do not add a model-backed prose verdict to CI.

Reconsider promotion only in a follow-up issue after a pinned offline release
produces at most 5% false or conflicting findings on both manifestos. The study
must classify every finding again and demonstrate unique signal beyond agnix.

