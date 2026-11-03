import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import extract

FIXTURES = Path(__file__).parent / "fixtures"
WORKLOADS = {
    "codex": (
        "codex_session.jsonl",
        "f17cdbb747a818cbd5520c4e18b9c23b0956bcb80038eeb780a7e4f806fa749d",
    ),
    "small": (
        "empty_session.jsonl",
        "f5cda5782cee466c77ebf35960cf6e379a04d53f5c5e7340fa4cc32e304fc7ec",
    ),
    "large": (
        "large_arc_session.jsonl",
        "ed79daae6badbb50dc49bc9e3fed95ce1d58ebf073d44300ea981c90596bccc7",
    ),
    "tool-heavy": (
        "full_session.jsonl",
        "4015dc50c847dc39b2cd325c9411ef8db419704d244d255f3943a705fbc56737",
    ),
    "compacted": (
        "compacted_session.jsonl",
        "e3ac81e4cf1c8c7b464e9ad84a0d61a13121a3eaa76f2a40ab9d0ccffb524d85",
    ),
}


def canonical_digest(fixture: str) -> str:
    result = extract.extract_all_streaming(str(FIXTURES / fixture))
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class ExtractorCharacterizationTests(unittest.TestCase):
    def test_representative_workloads_match_golden_output(self) -> None:
        for workload, (fixture, expected) in WORKLOADS.items():
            with self.subTest(workload=workload):
                self.assertEqual(canonical_digest(fixture), expected)

    def test_malformed_jsonl_records_are_skipped(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.jsonl"
            path.write_text('{"id":1}\nnot-json\n{"id":2}\n')
            records = list(extract.stream_raw_jsonl(path))
        self.assertEqual(records, [{"id": 1}, {"id": 2}])

    def test_head_tail_reads_remain_bounded(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "large.jsonl"
            size = 2 * extract.LITE_READ_BUF_SIZE + 17
            path.write_bytes(b"x" * size)
            head, tail, observed_size = extract.read_head_tail(path)
        self.assertEqual(observed_size, size)
        self.assertEqual(len(head), extract.LITE_READ_BUF_SIZE)
        self.assertEqual(len(tail), extract.LITE_READ_BUF_SIZE)

    def test_conversation_workloads_preserve_both_roles(self) -> None:
        for workload in ("codex", "large", "tool-heavy", "compacted"):
            fixture = WORKLOADS[workload][0]
            result = extract.extract_all_streaming(str(FIXTURES / fixture))
            roles = {item["role"] for item in result["conversation_arc"]}
            with self.subTest(workload=workload):
                self.assertTrue({"user", "assistant"}.issubset(roles))
