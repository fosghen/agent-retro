# ADR 0005: Use release-please behind the milestone gate

Status: accepted

## Context

Agent Retro uses Conventional Commits and keeps its public version in both
`pyproject.toml` and `SKILL.md`. A release is valid only when the capability
milestone and exact-main checks in `docs/RELEASES.md` pass. Version calculation,
changelog generation, tags, and GitHub Releases need one owner without turning a
merge or calendar event into implicit publication.

## Options considered

### release-please manifest mode

Release-please derives versions and notes from Conventional Commits, maintains a
release PR, supports Python releases and extra TOML or generic version files,
and can prepare actions in dry-run mode. Its manifest records the last released
version. The GitHub Action normally runs after pushes, but it can instead be
placed behind an explicitly invoked workflow.

This fits the repository's review-first model: generated version and changelog
changes arrive as a normal protected PR before any tag exists. The main risk is
that merging a release PR can create a release when the action is configured in
its usual push-driven form; this repository will not use that trigger.

### python-semantic-release

Python Semantic Release also derives versions from commit conventions and can
update a changelog, tag, and GitHub release. Its common `semantic-release
version` flow writes and commits release artifacts in the publishing job. That
duplicates the repository's protected-PR path and would need more custom
separation between preparation and publication.

### Repository-owned release script

A local script would make the milestone check easy to compose but would own
SemVer parsing, changelog rendering, commit traversal, and tag/release recovery.
Those are established release-tool responsibilities and are not product
differentiators for Agent Retro.

## Decision

Adopt a pinned release-please manifest configuration, invoked only through an
explicit workflow. The repository's dry-run gate executes first and remains
authoritative. Release-please may prepare or update a release PR only after that
gate succeeds; tag and GitHub Release publication requires a second explicit
invocation against the exact merged release commit.

Release-please is the sole owner of:

- `.release-please-manifest.json` and generated `CHANGELOG.md` entries;
- the project version in `pyproject.toml`;
- the skill metadata version in `SKILL.md` through `extra-files`;
- generated release commit text, tag, notes, and GitHub Release.

Humans and ordinary agents do not edit those generated values directly. Product
code may read them and deterministic checks may compare them.

## Rejected behavior

- No schedule or `push` trigger may publish or prepare a release.
- No workflow may bypass branch protection by committing to `main`.
- Merging an ordinary feature PR never creates a tag or GitHub Release.
- Release-please never overrides an incomplete milestone, dirty worktree,
  non-main revision, missing required check, or version mismatch.

## Consequences

The next slice can implement the milestone dry-run independently of GitHub write
authority. Publication remains a separate high-risk issue because it creates
public tags and releases. If release-please cannot preserve this two-step model
under a pinned version, reject it before enabling publication rather than
weakening the milestone gate.
