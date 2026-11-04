import unittest

from agent_retro.transcript_metadata import (
    buffered_jsonl_records,
    codex_metadata_lite,
    codex_prompt,
    extract_json_field,
    is_injected_user_text,
    parse_timestamp,
)


class TranscriptMetadataTests(unittest.TestCase):
    def test_json_field_preserves_escaped_content(self) -> None:
        text = r'"text":"She said \"hello\" at C:\\work"'
        self.assertEqual(extract_json_field(text, "text"), r"She said \"hello\" at C:\\work")
        self.assertIsNone(extract_json_field(text, "missing"))

    def test_buffered_records_skip_malformed_and_non_objects(self) -> None:
        text = '{"id":1}\nnot-json\n[]\n{"id":2}'
        self.assertEqual(list(buffered_jsonl_records(text)), [{"id": 1}, {"id": 2}])

    def test_injected_user_text_prefixes_are_detected(self) -> None:
        for text in (
            "<system-reminder>x",
            "<environment_context>x",
            "# AGENTS.md instructions for x",
        ):
            with self.subTest(text=text):
                self.assertTrue(is_injected_user_text(text))
        self.assertFalse(is_injected_user_text("actual request"))

    def test_codex_prompt_skips_injected_text_and_bounds_output(self) -> None:
        records = [
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "<system-reminder>skip"}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "x" * 250}],
                },
            },
        ]
        self.assertEqual(codex_prompt(records), "x" * 200)

    def test_timestamp_parser_accepts_utc_and_rejects_invalid_values(self) -> None:
        parsed = parse_timestamp("2026-11-04T10:00:00Z")
        if parsed is None:
            self.fail("valid UTC timestamp was rejected")
        offset = parsed.utcoffset()
        if offset is None:
            self.fail("UTC timestamp is naive")
        self.assertEqual(offset.total_seconds(), 0)
        for value in (None, "", "invalid"):
            with self.subTest(value=value):
                self.assertIsNone(parse_timestamp(value))

    def test_codex_metadata_uses_only_supplied_bounded_buffers(self) -> None:
        head = (
            '{"type":"session_meta","timestamp":"2026-11-04T10:00:00Z",'
            '"payload":{"id":"one","cwd":"/workspace","cli_version":"1.0"}}\n'
            '{"type":"response_item","timestamp":"2026-11-04T10:00:01Z",'
            '"payload":{"type":"message","role":"user","content":[{"text":"review"}]}}'
        )
        tail = '{"type":"event","timestamp":"2026-11-04T10:00:05Z"}'
        result = codex_metadata_lite(head, tail, 123)
        self.assertEqual(result["session_id"], "one")
        self.assertEqual(result["cwd"], "/workspace")
        self.assertEqual(result["version"], "1.0")
        self.assertEqual(result["duration_seconds"], 5)
        self.assertEqual(result["file_size_bytes"], 123)
        self.assertEqual(result["first_prompt"], "review")
        self.assertEqual(result["agent"], "codex")
