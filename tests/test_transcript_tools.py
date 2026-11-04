from agent_retro.transcript_tools import tool_call_summary


def test_primary_tool_fields_preserve_agent_and_shell_previews() -> None:
    agent = tool_call_summary(
        {
            "name": "Agent",
            "id": "one",
            "input": {"description": "scan", "prompt": "x" * 400, "run_in_background": True},
        },
        "t",
    )
    expected_preview = 300
    assert agent["agent_description"] == "scan"
    assert len(agent["agent_prompt_preview"]) == expected_preview
    assert agent["run_in_background"] is True
    shell = tool_call_summary({"name": "Bash", "input": {"command": "echo ok"}}, "t")
    assert shell["command"] == "echo ok"


def test_secondary_tool_fields_filter_tasks_questions_and_bound_mcp() -> None:
    task = tool_call_summary(
        {"name": "TaskUpdate", "input": {"id": "1", "status": "done", "extra": "drop"}},
        None,
    )
    assert task["task_detail"] == {"id": "1", "status": "done"}
    question = tool_call_summary(
        {"name": "AskUserQuestion", "input": {"questions": [{"question": "Proceed?"}]}},
        None,
    )
    assert question["questions"] == ["Proceed?"]
    mcp = tool_call_summary({"name": "mcp__demo", "input": {"value": "x" * 400}}, None)
    expected_preview = 300
    assert len(mcp["mcp_inputs_preview"]) == expected_preview
