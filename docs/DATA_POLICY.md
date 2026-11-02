# Local data policy

Agent Retro is local-first. Raw transcripts remain in their agent-owned source
directories and are never copied into the proposal store, reports, logs, tests,
exports, or repository.

## Stored data and retention

- Findings store hashes, source paths, timestamps, and redacted excerpts capped
  at 500 characters; derived evidence expires after 90 days by default.
- Proposals and append-only decision events remain until explicit deletion so
  approvals and implemented changes stay auditable.
- Generated reports expire after 90 days. Operational logs and failed-attempt
  details expire after 30 days.
- Credentials and complete tool output are excluded from every derived artifact.

Retention cleanup deletes only derived files below the configured state root.
Changing a retention period affects future cleanup and does not touch transcripts.

## Export and deletion

Exports contain validated proposal records and events, never transcript contents.
They must pass the same redaction and excerpt bounds as persisted evidence.
Deleting one artifact is idempotent and must reject paths outside the state root.
A full reset requires an explicit command and reports the files it will remove.

## Backup and recovery

Back up the SQLite database with SQLite's online backup API, not by copying a
live database file. Backups inherit the same local permissions and retention.
Run `PRAGMA integrity_check` before restore; keep the damaged database unchanged
until recovery succeeds, and restore into a new file before atomic replacement.

Schema migrations are transactional and versioned. A failed migration rolls back
without replacing the last usable database. If integrity cannot be restored, the
derived store may be rebuilt from local transcripts only after explicit consent.

## Failure handling

Redaction, export, cleanup, backup, and migration failures fail closed and remain
visible as bounded operational errors. They never trigger transcript upload,
unbounded logging, silent database replacement, or automatic source deletion.
