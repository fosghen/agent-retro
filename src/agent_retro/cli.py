"""Command-line entry point for Agent Retro."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from agent_retro import __version__


def parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    result = argparse.ArgumentParser(
        prog="agent-retro",
        description="Local-first retrospectives for coding agent sessions.",
    )
    result.add_argument("--version", action="version", version=__version__)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line application."""
    parser().parse_args(argv)
    return 0
