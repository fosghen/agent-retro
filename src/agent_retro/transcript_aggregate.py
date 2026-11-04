"""Typed transcript aggregation primitives."""

from __future__ import annotations

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


