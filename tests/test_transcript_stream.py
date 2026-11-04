from agent_retro.transcript_stream import new_stream_state, process_record


def test_stream_state_accumulates_session_tokens_tools_and_arc() -> None:
    state = new_stream_state("claude")
    process_record(
        state,
        {
            "sessionId": "one",
            "gitBranch": "main",
            "timestamp": "2026-11-04T10:00:00Z",
            "message": {
                "role": "assistant",
                "usage": {"input_tokens": 3},
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "id": "tool-1",
                        "input": {"file_path": "a.py"},
                    },
                    {"type": "text", "text": "A sufficiently long assistant update."},
                ],
            },
        },
    )
    process_record(
        state,
        {"timestamp": "2026-11-04T10:00:01Z", "message": {"role": "user", "content": "continue"}},
    )

    expected_tokens = 3
    assert state.session["session_id"] == "one"
    assert state.tokens["input_tokens"] == expected_tokens
    assert state.files == {"read": {"a.py"}}
    assert [item["role"] for item in state.arc] == ["assistant", "user"]
