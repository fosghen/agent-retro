from agent_retro.transcript_session import empty_session, finalize_session, record_session


def test_session_state_preserves_first_values_and_sorted_branches() -> None:
    session = empty_session("claude")
    record_session(
        session,
        {
            "sessionId": "one",
            "cwd": "/work",
            "gitBranch": "z-branch",
            "version": "1",
            "timestamp": "2026-11-04T10:00:00Z",
        },
    )
    record_session(
        session,
        {
            "sessionId": "ignored",
            "gitBranch": "a-branch",
            "timestamp": "2026-11-04T10:00:05Z",
        },
    )

    finalize_session(session)

    expected_duration = 5
    assert session["session_id"] == "one"
    assert session["git_branch"] == "z-branch"
    assert session["branches_seen"] == ["a-branch", "z-branch"]
    assert session["duration_seconds"] == expected_duration
