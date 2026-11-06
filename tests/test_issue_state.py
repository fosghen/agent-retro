import json
import unittest

from scripts.check_issue_state import IssueStateError, check


class IssueStateTests(unittest.TestCase):
    def test_accepts_matching_open_issue(self) -> None:
        check(204, json.dumps({"number": 204, "state": "OPEN"}))

    def test_rejects_missing_or_closed_issue(self) -> None:
        cases = (
            ({"number": 205, "state": "OPEN"}, "absent"),
            ({"number": 204, "state": "CLOSED"}, "must be open"),
        )
        for payload, message in cases:
            with self.subTest(payload=payload), self.assertRaisesRegex(IssueStateError, message):
                check(204, json.dumps(payload))
