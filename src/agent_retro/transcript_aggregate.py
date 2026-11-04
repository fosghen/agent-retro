"""Typed transcript aggregation primitives."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict

PRICING_LAST_VERIFIED = "2026-04-06"
PRICE_PER_M = {
    "input": 15.0,
    "output": 75.0,
    "cache_create": 18.75,
    "cache_read": 1.50,
}


class TokenTotals(TypedDict):
    """Token counters emitted by the transcript schema."""

    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int


def empty_token_totals() -> TokenTotals:
    """Create zeroed token counters."""
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }


def add_assistant_usage(totals: TokenTotals, role: object, usage: object) -> bool:
    """Add one assistant usage mapping and report whether it counted as a turn."""
    if role != "assistant" or not isinstance(usage, Mapping) or not usage:
        return False
    totals["input_tokens"] += _usage_int(usage, "input_tokens")
    totals["output_tokens"] += _usage_int(usage, "output_tokens")
    totals["cache_creation_input_tokens"] += _usage_int(usage, "cache_creation_input_tokens")
    totals["cache_read_input_tokens"] += _usage_int(usage, "cache_read_input_tokens")
    return True


def _usage_int(usage: Mapping[object, object], field: str) -> int:
    value = usage.get(field, 0)
    return value if isinstance(value, int) else 0


def estimated_cost(tokens: TokenTotals, agent: str = "claude") -> float | None:
    """Estimate Claude token cost while preserving null costs for other agents."""
    if agent != "claude":
        return None
    return (
        tokens["input_tokens"] / 1_000_000 * PRICE_PER_M["input"]
        + tokens["output_tokens"] / 1_000_000 * PRICE_PER_M["output"]
        + tokens["cache_creation_input_tokens"] / 1_000_000 * PRICE_PER_M["cache_create"]
        + tokens["cache_read_input_tokens"] / 1_000_000 * PRICE_PER_M["cache_read"]
    )


