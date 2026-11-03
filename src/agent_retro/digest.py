"""Privacy-safe change-only daily digest rendering."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from agent_retro.models import SessionOutcomeStatus

if TYPE_CHECKING:
    from agent_retro.models import DailyRun, DailySessionOutcome


def render_daily_digest(
    runs: tuple[DailyRun, ...], changes: tuple[tuple[str, str, str], ...]
) -> str | None:
    """Render derived counts, lifecycle changes, and current retry log pointers."""
    outcomes = [outcome for run in runs for outcome in run.outcomes]
    analyzed = sum(item.status is SessionOutcomeStatus.ANALYZED for item in outcomes)
    skipped = sum(item.status is SessionOutcomeStatus.SKIPPED for item in outcomes)
    latest: dict[str, DailySessionOutcome] = {}
    for outcome in outcomes:
        latest[outcome.session_hash] = outcome
    logs = list(
        dict.fromkeys(
            item.log_ref
            for item in latest.values()
            if item.status is SessionOutcomeStatus.FAILED and item.retryable
        )
    )
    if not analyzed and not skipped and not logs and not changes:
        return None

    lines = [
        "# Agent Retro daily digest",
        "",
        f"- Analyzed sessions: {analyzed}",
        f"- Skipped sessions: {skipped}",
    ]
    if changes:
        lines.extend(("", "## Proposal state changes"))
        for fingerprint, previous, current in changes:
            safe_id = hashlib.sha256(fingerprint.encode(), usedforsecurity=False).hexdigest()[:12]
            change = f"{previous} → {current}" if previous != current else f"created as {current}"
            lines.append(f"- `{safe_id}`: {change}")
    if logs:
        lines.extend(("", "## Actionable failures"))
        lines.extend(f"- `{log_ref}`" for log_ref in logs)
    return "\n".join(lines)
