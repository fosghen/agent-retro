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

## Findings

| Rule | Count | Classification | Reason |
|---|---:|---|---|
| ambiguous-or | 7 | low-value | Slash shorthand is understandable in context. |
| atomic | 39 | low-value | Explanatory prose may contain related clauses. |
| budget | 1 | conflict | Dogent's 60-instruction limit is not an accepted product limit. |
| command | 12 | conflict | Skills require context and explanation, not only commands. |
| concise | 1 | useful | Progressive disclosure can shorten the 288-line entrypoint. |
| conditional | 1 | low-value | The discovery branch is necessary and explicit. |
| crowded | 5 | conflict | Ten instructions per section is an unsupported limit. |
| emoji | 1 | low-value | The reported arrow communicates a path transformation. |
| emphasis | 1 | low-value | Normative emphasis identifies a safety threshold. |
| empty | 1 | conflict | A title before subsections is valid Markdown. |
| fence-language | 4 | useful | Language tags improve rendering and copying. |
| frontmatter | 1 | conflict | OpenAI guidance permits the existing `metadata` mapping. |
| hedging | 10 | low-value | Most findings describe conditional evidence honestly. |
| inline-code | 19 | low-value | Several phrases are prose rather than literals. |
| jargon | 7 | mixed: 4 useful | Expand REST, JSONL, USD, and MCP once; filenames are not jargon. |
| line-length | 46 | conflict | An 80-column prose limit is not an OpenAI requirement. |
| no-articles | 128 | conflict | Removing English articles damages readability. |
| ordered | 1 | low-value | The reported sentence is not a procedure. |
| passive | 5 | low-value | Passive voice is sometimes the clearest constraint. |
| punctuation | 146 | conflict | The rule mistakes wrapped Markdown lines for sentences. |
| referential | 2 | low-value | Both pronouns have adjacent, unambiguous antecedents. |
| section-level | 9 | conflict | Nested headings support progressive disclosure. |
| short-sections | 15 | conflict | Descriptive headings improve navigation. |
| simple | 2 | low-value | The reported clauses preserve required qualifications. |
| stale | 3 | mixed: 1 useful | Remove the price threshold; keep runtime and recency semantics. |
| terms | 1 | low-value | Agent and assistant name distinct transcript roles. |
| units | 12 | low-value | Units are present or implied by named metrics. |
| untrusted | 2 | low-value | The reported lines do not execute transcript instructions. |
| vague | 4 | low-value | The surrounding text supplies measurable criteria. |
| weak-verb | 1 | low-value | The branch instruction names a concrete outcome. |

Official OpenAI skill tooling supports optional frontmatter metadata and nested
resources, while the plugin validator accepts `agents/openai.yaml` interface
metadata. Those contracts take precedence over dogent's stylistic preferences.

