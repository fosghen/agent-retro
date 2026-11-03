"""Report issue-first development state as one compact JSON document."""

from __future__ import annotations

import json
import re
import shutil

# Executables are resolved explicitly and arguments are never shell-evaluated.
import subprocess  # nosec B404
import sys
from collections.abc import Callable

from scripts.check_change_limits import (
    MAX_COMMIT_LINES,
    MAX_COMMITS,
    MAX_PR_LINES,
    ChangeLimitError,
    count_lines,
)

ISSUE_BRANCH = re.compile(r"(?:^|/)issue-([1-9][0-9]*)(?:-|$)")
Query = Callable[..., str]


class WorkflowStatusError(RuntimeError):
    """The current workflow state cannot be read or is invalid."""


def execute(tool: str, *args: str) -> str:
    """Run one fixed-argument read-only query."""
    executable = shutil.which(tool)
    if executable is None:
        message = f"{tool} executable is unavailable"
        raise WorkflowStatusError(message)
    try:
        result = subprocess.run(  # noqa: S603  # nosec B603
            [executable, *args], check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or f"exit {error.returncode}"
        message = f"{tool} query failed: {detail}"
        raise WorkflowStatusError(message) from error
    return result.stdout.strip()
