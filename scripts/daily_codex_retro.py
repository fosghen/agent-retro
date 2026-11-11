#!/usr/bin/env python3
"""Run a read-only Codex retrospective over yesterday's local sessions."""

from __future__ import annotations

import argparse
import shutil

# Only the resolved Codex executable is invoked; arguments are not shell-evaluated.
import subprocess  # nosec B404
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def session_dir(home: Path, day: date) -> Path:
    """Return Codex's date-partitioned session directory."""
    return home / ".codex" / "sessions" / day.strftime("%Y/%m/%d")


def command(home: Path, day: date, report: Path) -> list[str]:
    """Build the non-interactive, read-only Codex invocation."""
    codex = shutil.which("codex")
    if codex is None:
        message = "codex CLI is unavailable"
        raise RuntimeError(message)
    prompt = (
        "Use the agent-retro skill to analyze only Codex sessions from "
        f"{session_dir(home, day)}. Identify repeated workflows and propose the "
        "smallest reusable skill or tool improvements. Do not modify any files. "
        "Return a concise Markdown report with evidence and no transcript excerpts."
    )
    return [
        codex,
        "exec",
        "--model",
        "gpt-6-luna",
        "--config",
        'model_reasoning_effort="medium"',
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--output-last-message",
        str(report),
        "--cd",
        str(home),
        prompt,
    ]


def parse_day(argv: Sequence[str], today: date) -> date:
    """Select an exact backfill day, defaulting to yesterday."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=date.fromisoformat)
    arguments = parser.parse_args(argv)
    return arguments.date or today - timedelta(days=1)


def run_day(home: Path, day: date) -> int:
    """Write one selected day's retrospective when session files exist."""
    source = session_dir(home, day)
    if not any(source.glob("*.jsonl")):
        return 0
    reports = home / ".codex" / "worklog" / "retros"
    reports.mkdir(parents=True, exist_ok=True)
    report = reports / f"{day.isoformat()}-daily.md"
    subprocess.run(  # noqa: S603  # nosec B603
        command(home, day, report), check=True
    )
    return 0


def main() -> int:
    """Write the requested retrospective, defaulting to yesterday."""
    today = datetime.now(tz=UTC).astimezone().date()
    return run_day(Path.home(), parse_day(sys.argv[1:], today))


if __name__ == "__main__":
    raise SystemExit(main())
