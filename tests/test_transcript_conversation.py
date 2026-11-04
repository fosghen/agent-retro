from agent_retro.transcript_conversation import assistant_arc_item, user_arc_item


def test_assistant_arc_filters_short_text_and_bounds_meaningful_text() -> None:
    meaningful_text = "x" * 21
    long_text = "x" * 1200
    assert assistant_arc_item({"text": "short"}, "assistant", "t") is None
    assert assistant_arc_item({"text": meaningful_text}, "user", "t") is None
    item = assistant_arc_item({"text": f"  {long_text}  "}, "assistant", "t")
    assert item is not None
    expected_length = 1000
    assert len(item["text"]) == expected_length
    assert item["timestamp"] == "t"


def test_user_arc_joins_list_content_and_excludes_injected_text() -> None:
    item = user_arc_item(
        [{"type": "text", "text": "hello "}, "world", {"type": "image"}],
        "user",
        "t",
    )
    assert item == {"role": "user", "text": "hello world", "timestamp": "t"}
    assert user_arc_item("<environment_context>secret", "user", "t") is None
    assert user_arc_item("actual request", "assistant", "t") is None
