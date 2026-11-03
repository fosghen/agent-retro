"""Transactional SQLite persistence for proposals."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from pathlib import Path  # noqa: TC003 -- public constructor accepts Path.
from typing import TYPE_CHECKING

from agent_retro.models import (
    MAX_PROPOSAL_EVIDENCE,
    SCHEMA_VERSION,
    AnalyzerCandidate,
    DailyRun,
    DailySessionOutcome,
    EvidenceReference,
    Proposal,
    ProposalObservation,
    ProposalRevision,
    ProposalStatus,
    SchemaError,
    SessionOutcomeStatus,
    StatusEvent,
    analyzer_candidate_from_mapping,
    proposal_from_mapping,
)

if TYPE_CHECKING:
    from collections.abc import Callable

STORE_VERSION = 5
PROMOTION_OCCURRENCES = 2
MAX_DECISION_REASON_CHARS = 1000


class ProposalStore:
    """Own the local proposal database and its migrations."""

    def __init__(self, path: Path, *, timeout: float = 0.05) -> None:
        """Configure a store without touching the filesystem."""
        self.path = path
        self.timeout = timeout

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=self.timeout)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        """Create or migrate the store atomically and idempotently."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > STORE_VERSION:
                message = f"unsupported store version: {version}"
                raise RuntimeError(message)
            if version == 0:
                self._migrate_v1(connection)
                version = 1
            if version == 1:
                self._migrate_v2(connection)
                version = 2
            if version == STORE_VERSION - 3:
                self._migrate_v3(connection)
                version = 3
            if version == STORE_VERSION - 2:
                self._migrate_v4(connection)
                version = 4
            if version == STORE_VERSION - 1:
                self._migrate_v5(connection)

    def _migrate_v1(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE proposals (fingerprint TEXT PRIMARY KEY, "
            "schema_version INTEGER NOT NULL, status TEXT NOT NULL, "
            "current_revision INTEGER NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE revisions (fingerprint TEXT NOT NULL, revision INTEGER NOT NULL, "
            "payload TEXT NOT NULL, PRIMARY KEY (fingerprint, revision))"
        )
        connection.execute(
            "CREATE TABLE events (id INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL, "
            "previous TEXT NOT NULL, current TEXT NOT NULL, occurred_at TEXT NOT NULL)"
        )
        connection.execute("PRAGMA user_version = 1")

    def _migrate_v2(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE occurrences (id INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL, "
            "intent TEXT NOT NULL, target TEXT NOT NULL, scope TEXT NOT NULL, "
            "source_hash TEXT NOT NULL, excerpt TEXT NOT NULL, "
            "UNIQUE(fingerprint, source_hash))"
        )
        connection.execute("PRAGMA user_version = 2")

    def _migrate_v3(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE decisions (id INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL, "
            "decision TEXT NOT NULL, revision INTEGER NOT NULL, occurred_at TEXT NOT NULL, "
            "reason TEXT, until_date TEXT)"
        )
        connection.execute("PRAGMA user_version = 3")

    def _migrate_v4(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE daily_runs (id INTEGER PRIMARY KEY, run_date TEXT NOT NULL, "
            "completed_at TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE daily_outcomes (run_id INTEGER NOT NULL, session_hash TEXT NOT NULL, "
            "status TEXT NOT NULL, detail TEXT NOT NULL, retryable INTEGER NOT NULL, "
            "log_ref TEXT, UNIQUE(run_id, session_hash), "
            "FOREIGN KEY(run_id) REFERENCES daily_runs(id))"
        )
        connection.execute("PRAGMA user_version = 4")

    def _migrate_v5(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE digest_cursor (singleton INTEGER PRIMARY KEY CHECK(singleton = 1), "
            "run_id INTEGER NOT NULL, event_id INTEGER NOT NULL)"
        )
        connection.execute("INSERT INTO digest_cursor VALUES (1, 0, 0)")
        connection.execute("PRAGMA user_version = 5")

    def record_daily_run(self, run: DailyRun) -> int:
        """Atomically persist one privacy-safe daily run summary."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._check_version(connection)
            cursor = connection.execute(
                "INSERT INTO daily_runs (run_date, completed_at) VALUES (?, ?)",
                (run.run_date, run.completed_at),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("daily run id was not generated")  # noqa: EM101, TRY003
            run_id = cursor.lastrowid
            connection.executemany(
                "INSERT INTO daily_outcomes VALUES (?, ?, ?, ?, ?, ?)",
                (
                    (
                        run_id,
                        item.session_hash,
                        item.status.value,
                        item.detail,
                        item.retryable,
                        item.log_ref,
                    )
                    for item in run.outcomes
                ),
            )
        return run_id

    @staticmethod
    def _daily_outcome(row: tuple[object, ...]) -> DailySessionOutcome:
        session_hash, status, detail, retryable, log_ref = row
        if (
            not isinstance(session_hash, str)
            or not isinstance(status, str)
            or not isinstance(detail, str)
            or not isinstance(retryable, int)
            or isinstance(retryable, bool)
            or retryable not in {0, 1}
            or (log_ref is not None and not isinstance(log_ref, str))
        ):
            raise SchemaError("invalid stored daily outcome")  # noqa: EM101, TRY003
        return DailySessionOutcome(
            session_hash,
            SessionOutcomeStatus(status),
            detail,
            bool(retryable),
            log_ref,
        )

    def list_daily_runs(self, *, after_id: int = 0) -> list[tuple[int, DailyRun]]:
        """Return daily runs and their derived outcomes in stable order."""
        if not isinstance(after_id, int) or isinstance(after_id, bool) or after_id < 0:
            raise ValueError("after_id must not be negative")  # noqa: EM101, TRY003
        with self._connect() as connection:
            self._check_version(connection)
            runs = connection.execute(
                "SELECT id, run_date, completed_at FROM daily_runs WHERE id > ? ORDER BY id",
                (after_id,),
            ).fetchall()
            result = []
            for run_id, run_date, completed_at in runs:
                rows = connection.execute(
                    "SELECT session_hash, status, detail, retryable, log_ref "
                    "FROM daily_outcomes WHERE run_id = ? ORDER BY rowid",
                    (run_id,),
                ).fetchall()
                outcomes = tuple(self._daily_outcome(row) for row in rows)
                result.append((int(run_id), DailyRun(str(run_date), str(completed_at), outcomes)))
        return result

    def retryable_failures(self) -> list[DailySessionOutcome]:
        """Return failed sessions with local logs for a later retry."""
        with self._connect() as connection:
            self._check_version(connection)
            rows = connection.execute(
                "SELECT o.session_hash, o.status, o.detail, o.retryable, o.log_ref "
                "FROM daily_outcomes o WHERE o.status = 'failed' AND o.retryable = 1 "
                "AND o.run_id = (SELECT max(n.run_id) FROM daily_outcomes n "
                "WHERE n.session_hash = o.session_hash) ORDER BY o.run_id, o.rowid"
            ).fetchall()
        return [self._daily_outcome(row) for row in rows]

    def _digest_snapshot(
        self, connection: sqlite3.Connection
    ) -> tuple[int, int, tuple[DailyRun, ...], tuple[tuple[str, str, str], ...]]:
        cursor_row = connection.execute(
            "SELECT run_id, event_id FROM digest_cursor WHERE singleton = 1"
        ).fetchone()
        maxima = connection.execute(
            "SELECT coalesce((SELECT max(id) FROM daily_runs), 0), "
            "coalesce((SELECT max(id) FROM events), 0)"
        ).fetchone()
        if cursor_row is None or any(
            not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= maximum
            for value, maximum in zip(cursor_row, maxima, strict=True)
        ):
            raise SchemaError("invalid stored digest cursor")  # noqa: EM101, TRY003
        run_cursor, event_cursor = cursor_row
        run_rows = connection.execute(
            "SELECT id, run_date, completed_at FROM daily_runs WHERE id > ? ORDER BY id",
            (run_cursor,),
        ).fetchall()
        runs = []
        for run_id, run_date, completed_at in run_rows:
            rows = connection.execute(
                "SELECT session_hash, status, detail, retryable, log_ref "
                "FROM daily_outcomes WHERE run_id = ? ORDER BY rowid",
                (run_id,),
            ).fetchall()
            outcomes = tuple(self._daily_outcome(row) for row in rows)
            runs.append(DailyRun(str(run_date), str(completed_at), outcomes))
        event_rows = connection.execute(
            "SELECT id, fingerprint, previous, current FROM events WHERE id > ? ORDER BY id",
            (event_cursor,),
        ).fetchall()
        changes = tuple(
            (
                str(fingerprint),
                ProposalStatus(str(previous)).value,
                ProposalStatus(str(current)).value,
            )
            for _, fingerprint, previous, current in event_rows
        )
        run_id = int(run_rows[-1][0]) if run_rows else int(run_cursor)
        event_id = int(event_rows[-1][0]) if event_rows else int(event_cursor)
        return run_id, event_id, tuple(runs), changes

    def save(self, proposal: Proposal, event: StatusEvent) -> None:
        """Atomically store one proposal revision and its append-only event."""
        if event.fingerprint != proposal.fingerprint or event.current != proposal.status:
            message = "event must describe the persisted proposal state"
            raise ValueError(message)
        payload = json.dumps(asdict(proposal.revision), sort_keys=True)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO proposals VALUES (?, ?, ?, ?) "
                "ON CONFLICT(fingerprint) DO UPDATE SET schema_version=excluded.schema_version, "
                "status=excluded.status, current_revision=excluded.current_revision",
                (
                    proposal.fingerprint,
                    proposal.schema_version,
                    proposal.status.value,
                    proposal.revision.number,
                ),
            )
            connection.execute(
                "INSERT OR IGNORE INTO revisions VALUES (?, ?, ?)",
                (proposal.fingerprint, proposal.revision.number, payload),
            )
            connection.execute(
                "INSERT INTO events (fingerprint, previous, current, occurred_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    event.fingerprint,
                    event.previous.value,
                    event.current.value,
                    event.occurred_at,
                ),
            )

    @staticmethod
    def _proposal(row: tuple[object, ...]) -> Proposal:
        schema_version, fingerprint, status, payload = row
        revision = json.loads(str(payload))
        return proposal_from_mapping(
            {
                "schema_version": schema_version,
                "fingerprint": fingerprint,
                "status": status,
                "revision": revision,
            }
        )

    @staticmethod
    def _check_version(connection: sqlite3.Connection) -> None:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > STORE_VERSION:
            raise ValueError(f"unsupported store version: {version}")  # noqa: EM102, TRY003

    def list_proposals(self, status: ProposalStatus | None = None) -> list[Proposal]:
        """Return current proposals in stable fingerprint order."""
        query = (
            "SELECT p.schema_version, p.fingerprint, p.status, r.payload "
            "FROM proposals p LEFT JOIN revisions r ON r.fingerprint = p.fingerprint "
            "AND r.revision = p.current_revision"
        )
        parameters: tuple[str, ...] = ()
        if status is not None:
            query += " WHERE p.status = ?"
            parameters = (status.value,)
        query += " ORDER BY p.fingerprint"
        with self._connect() as connection:
            self._check_version(connection)
            rows = connection.execute(query, parameters).fetchall()
        return [self._proposal(row) for row in rows]

    def get(self, fingerprint: str) -> Proposal | None:
        """Return one current proposal, or ``None`` when it is absent."""
        with self._connect() as connection:
            self._check_version(connection)
            row = connection.execute(
                "SELECT p.schema_version, p.fingerprint, p.status, r.payload "
                "FROM proposals p LEFT JOIN revisions r ON r.fingerprint = p.fingerprint "
                "AND r.revision = p.current_revision WHERE p.fingerprint = ?",
                (fingerprint,),
            ).fetchone()
        return None if row is None else self._proposal(row)

    def approved_revision(self, fingerprint: str) -> ProposalRevision | None:
        """Return the immutable revision frozen by approval."""
        with self._connect() as connection:
            self._check_version(connection)
            row = connection.execute(
                "SELECT p.schema_version, p.fingerprint, p.status, r.payload "
                "FROM decisions d JOIN proposals p ON p.fingerprint = d.fingerprint "
                "JOIN revisions r ON r.fingerprint = d.fingerprint AND r.revision = d.revision "
                "WHERE d.fingerprint = ? AND d.decision = 'approved' ORDER BY d.id LIMIT 1",
                (fingerprint,),
            ).fetchone()
        return None if row is None else self._proposal(row).revision

    def approve(self, fingerprint: str, revision: int, occurred_at: str) -> Proposal:
        """Atomically approve and freeze the current reviewed revision."""
        return self._decide(fingerprint, ProposalStatus.APPROVED, occurred_at, revision=revision)

    def reject(self, fingerprint: str, reason: str, occurred_at: str) -> Proposal:
        """Atomically reject a proposal with a bounded reason."""
        if (
            not isinstance(reason, str)
            or not reason.strip()
            or len(reason) > MAX_DECISION_REASON_CHARS
        ):
            raise SchemaError("rejection reason must contain at most 1000 characters")  # noqa: EM101, TRY003
        return self._decide(fingerprint, ProposalStatus.REJECTED, occurred_at, reason=reason)

    def defer(self, fingerprint: str, until_date: str, occurred_at: str) -> Proposal:
        """Atomically defer a proposal until an ISO calendar date."""
        try:
            valid_date = date.fromisoformat(until_date)
        except (TypeError, ValueError) as error:
            raise SchemaError("deferral date must use YYYY-MM-DD") from error  # noqa: EM101, TRY003
        if valid_date.isoformat() != until_date:
            raise SchemaError("deferral date must use YYYY-MM-DD")  # noqa: EM101, TRY003
        return self._decide(
            fingerprint, ProposalStatus.DEFERRED, occurred_at, until_date=until_date
        )

    def _decide(  # noqa: PLR0913
        self,
        fingerprint: str,
        target: ProposalStatus,
        occurred_at: str,
        *,
        revision: int | None = None,
        reason: str | None = None,
        until_date: str | None = None,
    ) -> Proposal:
        if not isinstance(occurred_at, str) or not occurred_at.strip():
            raise SchemaError("decision timestamp is required")  # noqa: EM101, TRY003
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._check_version(connection)
            row = connection.execute(
                "SELECT p.schema_version, p.fingerprint, p.status, r.payload "
                "FROM proposals p JOIN revisions r ON r.fingerprint = p.fingerprint "
                "AND r.revision = p.current_revision WHERE p.fingerprint = ?",
                (fingerprint,),
            ).fetchone()
            if row is None:
                raise SchemaError("proposal not found")  # noqa: EM101, TRY003
            current = self._proposal(row)
            if revision is not None and current.revision.number != revision:
                raise SchemaError("reviewed revision is stale")  # noqa: EM101, TRY003
            decided = current.transition(target)
            connection.execute(
                "INSERT INTO decisions "
                "(fingerprint, decision, revision, occurred_at, reason, until_date) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    fingerprint,
                    target.value,
                    current.revision.number,
                    occurred_at,
                    reason,
                    until_date,
                ),
            )
            connection.execute(
                "UPDATE proposals SET status = ? WHERE fingerprint = ?",
                (decided.status.value, fingerprint),
            )
            connection.execute(
                "INSERT INTO events (fingerprint, previous, current, occurred_at) "
                "VALUES (?, ?, ?, ?)",
                (fingerprint, current.status.value, decided.status.value, occurred_at),
            )
        return decided

    def record_observation(self, observation: ProposalObservation) -> bool:
        """Persist one distinct source observation and report whether it was new."""
        with self._connect() as connection:
            self._check_version(connection)
            return self._insert_observation(connection, observation)

    @staticmethod
    def _insert_observation(
        connection: sqlite3.Connection, observation: ProposalObservation
    ) -> bool:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO occurrences "
            "(fingerprint, intent, target, scope, source_hash, excerpt) VALUES (?, ?, ?, ?, ?, ?)",
            (
                observation.fingerprint,
                observation.intent,
                observation.target,
                observation.scope,
                observation.evidence.source_hash,
                observation.evidence.excerpt,
            ),
        )
        return cursor.rowcount == 1

    def list_observations(self, fingerprint: str) -> list[ProposalObservation]:
        """Return distinct observations in stable arrival order."""
        with self._connect() as connection:
            self._check_version(connection)
            rows = connection.execute(
                "SELECT intent, target, scope, source_hash, excerpt FROM occurrences "
                "WHERE fingerprint = ? ORDER BY id",
                (fingerprint,),
            ).fetchall()
        return [
            ProposalObservation(intent, target, scope, EvidenceReference(source_hash, excerpt))
            for intent, target, scope, source_hash, excerpt in rows
        ]

    def occurrence_count(self, fingerprint: str) -> int:
        """Return the number of distinct sources recorded for one identity."""
        with self._connect() as connection:
            self._check_version(connection)
            row = connection.execute(
                "SELECT count(*) FROM occurrences WHERE fingerprint = ?", (fingerprint,)
            ).fetchone()
        return int(row[0])

    def aggregate_observation(
        self,
        observation: ProposalObservation,
        *,
        occurred_at: str | None = None,
        template: AnalyzerCandidate | None = None,
    ) -> Proposal | None:
        """Record evidence and promote recurring observations atomically."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._check_version(connection)
            inserted = self._insert_observation(connection, observation)
            rows = connection.execute(
                "SELECT intent, target, scope, source_hash, excerpt FROM occurrences "
                "WHERE fingerprint = ? ORDER BY id",
                (observation.fingerprint,),
            ).fetchall()
            if len(rows) < PROMOTION_OCCURRENCES:
                return None
            current_row = connection.execute(
                "SELECT p.schema_version, p.fingerprint, p.status, r.payload "
                "FROM proposals p JOIN revisions r ON r.fingerprint = p.fingerprint "
                "AND r.revision = p.current_revision WHERE p.fingerprint = ?",
                (observation.fingerprint,),
            ).fetchone()
            current = None if current_row is None else self._proposal(current_row)
            if current is not None and not inserted:
                return current
            if current is not None and current.status not in {
                ProposalStatus.NEW,
                ProposalStatus.APPROVED,
                ProposalStatus.REJECTED,
            }:
                return current
            evidence = tuple(
                EvidenceReference(source_hash, excerpt)
                for _, _, _, source_hash, excerpt in rows[-MAX_PROPOSAL_EVIDENCE:]
            )
            if current is None:
                intent, target, scope, _, _ = rows[0]
                revision = (
                    replace(template.revision(), evidence=evidence)
                    if template is not None
                    else ProposalRevision(
                        1,
                        " ".join(intent.split()),
                        f"Observed in {len(rows)} distinct sources.",
                        target,
                        evidence,
                        problem=intent,
                        affected_workflow=target,
                        proposed_artifact=target,
                        scope=scope,
                    )
                )
                proposal = Proposal(
                    SCHEMA_VERSION, observation.fingerprint, ProposalStatus.NEW, revision
                )
                connection.execute(
                    "INSERT INTO proposals VALUES (?, ?, ?, ?)",
                    (proposal.fingerprint, proposal.schema_version, proposal.status.value, 1),
                )
            else:
                revision = (
                    replace(
                        template.revision(),
                        number=current.revision.number + 1,
                        evidence=evidence,
                    )
                    if template is not None
                    else replace(
                        current.revision,
                        number=current.revision.number + 1,
                        rationale=f"Observed in {len(rows)} distinct sources.",
                        evidence=evidence,
                    )
                )
                reopened = current.status is ProposalStatus.REJECTED
                if reopened and not occurred_at:
                    message = "occurred_at is required to reopen rejected evidence"
                    raise ValueError(message)
                proposal = replace(
                    current,
                    status=ProposalStatus.NEW if reopened else current.status,
                    revision=revision,
                )
                connection.execute(
                    "UPDATE proposals SET status = ?, current_revision = ? WHERE fingerprint = ?",
                    (proposal.status.value, revision.number, proposal.fingerprint),
                )
            connection.execute(
                "INSERT INTO revisions VALUES (?, ?, ?)",
                (
                    proposal.fingerprint,
                    revision.number,
                    json.dumps(asdict(revision), sort_keys=True),
                ),
            )
            if current is None:
                connection.execute(
                    "INSERT INTO events (fingerprint, previous, current, occurred_at) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        proposal.fingerprint,
                        ProposalStatus.NEW.value,
                        ProposalStatus.NEW.value,
                        occurred_at or datetime.now(UTC).isoformat(),
                    ),
                )
            elif current.status is ProposalStatus.REJECTED:
                connection.execute(
                    "INSERT INTO events (fingerprint, previous, current, occurred_at) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        proposal.fingerprint,
                        ProposalStatus.REJECTED.value,
                        ProposalStatus.NEW.value,
                        occurred_at,
                    ),
                )
        return proposal

    def ingest_analyzer_output(
        self, value: object, *, occurred_at: str | None = None
    ) -> Proposal | None:
        """Validate a candidate completely before starting durable ingestion."""
        return self.ingest_candidate(
            analyzer_candidate_from_mapping(value), occurred_at=occurred_at
        )

    def ingest_candidate(
        self, candidate: AnalyzerCandidate, *, occurred_at: str | None = None
    ) -> Proposal | None:
        """Persist an already validated analyzer candidate."""
        return self.aggregate_observation(
            candidate.observation, occurred_at=occurred_at, template=candidate
        )
