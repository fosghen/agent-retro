"""Transactional SQLite persistence for proposals."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, replace
from pathlib import Path  # noqa: TC003 -- public constructor accepts Path.

from agent_retro.models import (
    MAX_PROPOSAL_EVIDENCE,
    SCHEMA_VERSION,
    AnalyzerCandidate,
    EvidenceReference,
    Proposal,
    ProposalObservation,
    ProposalRevision,
    ProposalStatus,
    StatusEvent,
    analyzer_candidate_from_mapping,
    proposal_from_mapping,
)

STORE_VERSION = 2
PROMOTION_OCCURRENCES = 2


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
            if current is not None and current.status is ProposalStatus.REJECTED:
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
