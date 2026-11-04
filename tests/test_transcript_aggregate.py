from agent_retro.transcript_aggregate import (
    TokenTotals,
    add_assistant_usage,
    empty_token_totals,
    estimated_cost,
)


def test_usage_counts_only_nonempty_assistant_mappings() -> None:
    totals = empty_token_totals()
    assert not add_assistant_usage(totals, "user", {"input_tokens": 99})
    assert not add_assistant_usage(totals, "assistant", {})
    assert not add_assistant_usage(totals, "assistant", "invalid")
    assert add_assistant_usage(
        totals,
        "assistant",
        {
            "input_tokens": 10,
            "output_tokens": 20,
            "cache_creation_input_tokens": 30,
            "cache_read_input_tokens": 40,
        },
    )
    assert totals == {
        "input_tokens": 10,
        "output_tokens": 20,
        "cache_creation_input_tokens": 30,
        "cache_read_input_tokens": 40,
    }


def test_cost_preserves_claude_pricing_and_other_agent_null() -> None:
    totals: TokenTotals = {
        "input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
        "cache_creation_input_tokens": 1_000_000,
        "cache_read_input_tokens": 1_000_000,
    }
    expected_cost = 110.25
    assert estimated_cost(totals) == expected_cost
    assert estimated_cost(totals, "codex") is None
