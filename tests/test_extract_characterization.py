import hashlib
import json
import unittest
from pathlib import Path

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
