import json
import subprocess
import unittest
from unittest.mock import patch

from scripts.workflow_status import WorkflowStatusError, collect, encode, execute, main

RESPONSES = {
    ("git", "branch", "--show-current"): "feature/issue-102-status",
    ("git", "rev-list", "--count", "origin/main..HEAD"): "2",
    ("git", "diff", "--numstat", "origin/main...HEAD"): "40\t10\tfile.py",
    ("git", "diff", "--cached", "--numstat"): "7\t3\tfile.py",
    ("gh", "issue", "view", "102", "--json", "number,state"): '{"number":102,"state":"OPEN"}',
    (
        "gh",
        "pr",
        "list",
        "--head",
        "feature/issue-102-status",
        "--state",
        "all",
        "--limit",
        "1",
        "--json",
        "state",
    ): '[{"state":"OPEN"}]',
}


def query(tool: str, *args: str) -> str:
    return RESPONSES[(tool, *args)]


class WorkflowStatusTests(unittest.TestCase):
    def test_collects_compact_issue_first_state_and_budgets(self) -> None:
        status = collect(query)
        self.assertEqual(status["issue"], {"number": 102, "state": "OPEN"})
        self.assertEqual(status["pr_state"], "OPEN")
        self.assertEqual(status["commits"], 2)
        self.assertEqual(status["changed_lines"], 50)
        self.assertEqual(status["remaining"], {"commit_lines": 40, "commits": 3, "pr_lines": 200})
        self.assertNotIn(" ", encode(status))
