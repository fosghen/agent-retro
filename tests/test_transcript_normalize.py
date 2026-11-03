import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_retro.transcript_normalize import (
    json_object,
    normalize_codex_content,
    normalize_codex_record,
    normalize_codex_tool,
    stream_normalized_jsonl,
)


class TranscriptNormalizeTests(unittest.TestCase):
    def test_content_keeps_only_shared_text_blocks(self) -> None:
        content = [
            {"type": "input_text", "text": "input"},
            {"type": "output_text", "text": "output"},
            {"type": "image", "url": "ignored"},
            "ignored",
        ]
        self.assertEqual(
            normalize_codex_content(content),
            [{"type": "text", "text": "input"}, {"type": "text", "text": "output"}],
        )
        self.assertEqual(normalize_codex_content("unchanged"), "unchanged")

    def test_json_object_rejects_invalid_or_non_object_values(self) -> None:
        self.assertEqual(json_object('{"value":1}'), {"value": 1})
        for value in ("invalid", "[]", None):
            with self.subTest(value=value):
                self.assertEqual(json_object(value), {})

    def test_custom_and_function_calls_are_normalized(self) -> None:
        custom = {"type": "custom_tool_call", "name": "exec", "call_id": "one", "input": "pwd"}
        function = {"type": "function_call", "name": "read", "arguments": '{"path":"a"}'}
        self.assertEqual(normalize_codex_tool(custom)["input"], {"command": "pwd"})
        self.assertEqual(normalize_codex_tool(function)["input"], {"path": "a"})

    def test_spawn_agent_preserves_dispatch_shape(self) -> None:
        payload = {
            "type": "function_call",
            "name": "collaboration.spawn_agent",
            "call_id": "agent",
            "arguments": '{"task_name":"scan","model":"gpt","message":"inspect"}',
        }
        normalized = normalize_codex_tool(payload)
        self.assertEqual(normalized["name"], "Agent")
        self.assertEqual(
            normalized["input"],
            {"description": "scan", "subagent_type": "scan", "model": "gpt", "prompt": "inspect"},
        )

    def test_session_and_usage_records_are_normalized(self) -> None:
        session = {"type": "session_meta", "payload": {"id": "one", "cwd": "/workspace"}}
        usage = {
            "type": "token_usage_record",
            "timestamp": "now",
            "payload": {"usage": {"input_tokens": 10, "cached_input_tokens": 4}},
        }
        self.assertEqual(normalize_codex_record(session)["sessionId"], "one")
        normalized_usage = normalize_codex_record(usage)["message"]["usage"]
        self.assertEqual(normalized_usage["input_tokens"], 6)
        self.assertEqual(normalized_usage["cache_read_input_tokens"], 4)

    def test_response_record_roles_are_normalized(self) -> None:
        message = {"type": "response_item", "payload": {"type": "message", "role": "user"}}
        call = {"type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec"}}
        output = {
            "type": "response_item",
            "payload": {"type": "custom_tool_call_output", "call_id": "one", "output": "ok"},
        }
        self.assertEqual(normalize_codex_record(message)["message"]["role"], "user")
        self.assertEqual(normalize_codex_record(call)["message"]["role"], "assistant")
        self.assertEqual(normalize_codex_record(output)["message"]["role"], "user")

    def test_claude_stream_records_pass_through_unchanged(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "claude.jsonl"
            path.write_text('{"sessionId":"one","value":2}\n')
            records = list(stream_normalized_jsonl(str(path)))
        self.assertEqual(records, [{"sessionId": "one", "value": 2}])
