"""Command-line entry point for Agent Retro."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from agent_retro import __version__
from agent_retro.models import Proposal, ProposalStatus
from agent_retro.store import ProposalStore

MAX_EVIDENCE_CHARS = 500
MAX_EVIDENCE_ITEMS = 5
MAX_SOURCE_HASH_CHARS = 128

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
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line application."""
    arguments = parser().parse_args(argv)
    if arguments.command is None:
        return 0
    if not arguments.store.exists():
        if arguments.command == "list":
            _write("No proposals.")
            return 0
        _write(f"Proposal not found: {arguments.proposal_id}", error=True)
        return 1

    store = ProposalStore(arguments.store)
    try:
        if arguments.command == "list":
            return _list(store, arguments.status)
        return _show(store, arguments.proposal_id)
    except (sqlite3.DatabaseError, ValueError):
        _write("Cannot read proposal store: invalid or unsupported data.", error=True)
        return 1
