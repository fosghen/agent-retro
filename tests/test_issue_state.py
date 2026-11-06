import json
import unittest
from unittest.mock import patch

from scripts.check_issue_state import IssueStateError, check, main


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

    def test_main_reads_branch_and_fails_closed(self) -> None:
        with (
            patch.dict("os.environ", {"HEAD_BRANCH": "fix/issue-204-open"}),
            patch("scripts.check_issue_state.query") as query,
        ):
            query.return_value = '{"number":204,"state":"OPEN"}'
            self.assertEqual(main(), 0)
            query.return_value = '{"number":204,"state":"CLOSED"}'
            self.assertEqual(main(), 1)
