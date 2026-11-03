#!/usr/bin/env python3
"""Run a read-only Codex retrospective over yesterday's local sessions."""

from __future__ import annotations

import shutil

# Only the resolved Codex executable is invoked; arguments are not shell-evaluated.
import subprocess  # nosec B404
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


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
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--output-last-message",
        str(report),
        "--cd",
        str(home),
        prompt,
    ]


def main() -> int:
    """Write yesterday's retrospective when session files exist."""
    home = Path.home()
    day = datetime.now(tz=UTC).astimezone().date() - timedelta(days=1)
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


if __name__ == "__main__":
    raise SystemExit(main())
