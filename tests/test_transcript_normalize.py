import unittest

from agent_retro.transcript_normalize import (
    json_object,
    normalize_codex_content,
    normalize_codex_tool,
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
