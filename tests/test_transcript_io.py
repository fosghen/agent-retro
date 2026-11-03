import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_retro.transcript_io import (
    LITE_READ_BUF_SIZE,
    detect_transcript_format,
    read_head_tail,
    stream_raw_jsonl,
)


class TranscriptIOTests(unittest.TestCase):
    def test_stream_skips_blank_malformed_and_non_object_records(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "mixed.jsonl"
            path.write_text('\n{"id":1}\nnot-json\n[]\n{"id":2}\n')
            records = list(stream_raw_jsonl(path))
        self.assertEqual(records, [{"id": 1}, {"id": 2}])

    def test_detects_codex_and_defaults_to_claude(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            codex = root / "codex.jsonl"
            codex.write_text('{"type":"session_meta","payload":{}}\n')
            claude = root / "claude.jsonl"
            claude.write_text('{"sessionId":"one"}\n')
            empty = root / "empty.jsonl"
            empty.write_text("")
            self.assertEqual(detect_transcript_format(codex), "codex")
            self.assertEqual(detect_transcript_format(claude), "claude")
            self.assertEqual(detect_transcript_format(empty), "claude")

    def test_head_tail_read_is_bounded(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "large.jsonl"
            size = 2 * LITE_READ_BUF_SIZE + 17
            path.write_bytes(b"x" * size)
            head, tail, observed = read_head_tail(path)
        self.assertEqual(observed, size)
        self.assertEqual(len(head), LITE_READ_BUF_SIZE)
        self.assertEqual(len(tail), LITE_READ_BUF_SIZE)
