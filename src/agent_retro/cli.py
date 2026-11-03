"""Command-line entry point for Agent Retro."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from agent_retro import __version__
from agent_retro.digest import render_daily_digest
from agent_retro.models import (
    MAX_EXCERPT_CHARS,
    MAX_PROPOSAL_EVIDENCE,
    MAX_SOURCE_HASH_CHARS,
    DailyRun,
    Proposal,
    ProposalStatus,
)
from agent_retro.store import ProposalStore

if TYPE_CHECKING:
    from collections.abc import Sequence


def parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    result = argparse.ArgumentParser(
        prog="agent-retro",
        description="Local-first retrospectives for coding agent sessions.",
    )
    result.add_argument("--version", action="version", version=__version__)
    result.add_argument(
        "--store",
        type=Path,
        default=Path.home() / ".local" / "state" / "agent-retro" / "proposals.sqlite3",
        help="path to the local proposal database",
    )
    commands = result.add_subparsers(dest="command")
    list_parser = commands.add_parser("list", help="list proposal summaries")
    list_parser.add_argument("--status", type=ProposalStatus, choices=list(ProposalStatus))
    show_parser = commands.add_parser("show", help="show one proposal revision")
    show_parser.add_argument("proposal_id")
    approve_parser = commands.add_parser("approve", help="approve the current proposal revision")
    approve_parser.add_argument("proposal_id")
    approve_parser.add_argument("--revision", type=int, required=True)
    reject_parser = commands.add_parser("reject", help="reject a proposal")
    reject_parser.add_argument("proposal_id")
    reject_parser.add_argument("--reason", required=True)
    defer_parser = commands.add_parser("defer", help="defer a proposal")
    defer_parser.add_argument("proposal_id")
    defer_parser.add_argument("--until", required=True)
    commands.add_parser("digest", help="print unseen privacy-safe daily changes")
    return result


def _write(text: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    stream.write(f"{text}\n")


def _print_proposal(proposal: Proposal) -> None:
    """Print the bounded fields available in the current proposal schema."""
    fields = (
        ("ID", proposal.fingerprint),
        ("Status", proposal.status.value),
        ("Revision", proposal.revision.number),
        ("Title", proposal.revision.title),
        ("Rationale", proposal.revision.rationale),
        ("Target", proposal.revision.target),
        ("Problem", proposal.revision.problem),
        ("Affected workflow", proposal.revision.affected_workflow),
        ("Proposed artifact", proposal.revision.proposed_artifact),
        ("Expected benefit", proposal.revision.expected_benefit),
        ("Risks", proposal.revision.risks),
        ("Scope", proposal.revision.scope),
        ("Validation", proposal.revision.validation),
    )
    for label, value in fields:
        _write(f"{label}: {value}")
    _write("Evidence:")
    for evidence in proposal.revision.evidence[:MAX_PROPOSAL_EVIDENCE]:
        source_hash = evidence.source_hash[:MAX_SOURCE_HASH_CHARS]
        _write(f"- {source_hash}: {evidence.excerpt[:MAX_EXCERPT_CHARS]}")
    if len(proposal.revision.evidence) > MAX_PROPOSAL_EVIDENCE:
        _write("- Additional evidence omitted.")


def _list(store: ProposalStore, status: ProposalStatus | None) -> int:
    proposals = store.list_proposals(status)
    if not proposals:
        _write("No proposals.")
    for proposal in proposals:
        _write(f"{proposal.fingerprint}\t{proposal.status.value}\t{proposal.revision.title}")
    return 0


def _show(store: ProposalStore, proposal_id: str) -> int:
    proposal = store.get(proposal_id)
    if proposal is None:
        _write(f"Proposal not found: {proposal_id}", error=True)
        return 1
    _print_proposal(proposal)
    return 0


def _approve(store: ProposalStore, proposal_id: str, revision: int) -> int:
    approved = store.approve(proposal_id, revision, datetime.now(UTC).isoformat())
    _write(f"Approved revision {approved.revision.number}: {proposal_id}")
    return 0


def _reject(store: ProposalStore, proposal_id: str, reason: str) -> int:
    store.reject(proposal_id, reason, datetime.now(UTC).isoformat())
    _write(f"Rejected: {proposal_id}")
    return 0


def _defer(store: ProposalStore, proposal_id: str, until_date: str) -> int:
    store.defer(proposal_id, until_date, datetime.now(UTC).isoformat())
    _write(f"Deferred until {until_date}: {proposal_id}")
    return 0


def _digest(store: ProposalStore) -> int:
    store.initialize()

    def output(runs: tuple[DailyRun, ...], changes: tuple[tuple[str, str, str], ...]) -> bool:
        rendered = render_daily_digest(runs, changes)
        if rendered is None:
            return False
        _write(rendered)
        return True

    store.consume_digest(output)
    return 0


def main(argv: Sequence[str] | None = None) -> int:  # noqa: C901, PLR0911
    """Run the command-line application."""
    arguments = parser().parse_args(argv)
    if arguments.command is None:
        return 0
    if not arguments.store.exists():
        if arguments.command == "digest":
            return 0
        if arguments.command == "list":
            _write("No proposals.")
            return 0
        _write(f"Proposal not found: {arguments.proposal_id}", error=True)
        return 1

    store = ProposalStore(arguments.store)
    try:
        if arguments.command == "list":
            return _list(store, arguments.status)
        if arguments.command == "approve":
            return _approve(store, arguments.proposal_id, arguments.revision)
        if arguments.command == "reject":
            return _reject(store, arguments.proposal_id, arguments.reason)
        if arguments.command == "defer":
            return _defer(store, arguments.proposal_id, arguments.until)
        if arguments.command == "digest":
            return _digest(store)
        return _show(store, arguments.proposal_id)
    except (sqlite3.DatabaseError, RuntimeError, ValueError):
        action = (
            "read proposal store"
            if arguments.command in {"list", "show", "digest"}
            else "update proposal"
        )
        _write(f"Cannot {action}: invalid or unsupported data.", error=True)
        return 1
