import unittest

from agent_retro.transcript_metadata import (
    buffered_jsonl_records,
    codex_prompt,
    extract_json_field,
    is_injected_user_text,
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
