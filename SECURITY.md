# Security Policy

## Supported versions

Agent Retro is pre-1.0. Security fixes target the latest `main` revision and the
latest tagged release when one exists. Older revisions are not guaranteed to
receive fixes.

## Report a vulnerability privately

Use GitHub's private
[vulnerability reporting form](https://github.com/fosghen/agent-retro/security/advisories/new).
Do not open a public issue or pull request for an undisclosed vulnerability.

Include the affected revision or version, the impact, a minimal sanitized
reproduction, and any known mitigation. Reports may cover, for example:

- exposure of Codex transcripts, prompts, credentials, or private source;
- unsafe path, symlink, permission, or cleanup behavior in installation;
- command execution or trust-boundary violations;
- exploitable dependency vulnerabilities.

Never include real session transcripts, credentials, tokens, private repository
content, or internal infrastructure details. Replace them with synthetic values.
If a sensitive value was exposed, rotate it through its owning system rather than
placing it in the report.

The maintainer will coordinate validation, remediation, and disclosure through
the private advisory. No fixed response or remediation time is promised.

## Public disclosure

Publish details only after a fix or mitigation is available and disclosure has
been coordinated. Ordinary non-security defects should use the public issue
tracker.
