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

    def test_reports_missing_issue_branch_before_other_queries(self) -> None:
        calls: list[tuple[str, ...]] = []

        def missing_issue(tool: str, *args: str) -> str:
            calls.append((tool, *args))
            return "feature/topic"

        with self.assertRaisesRegex(WorkflowStatusError, "issue-N"):
            collect(missing_issue)
        self.assertEqual(calls, [("git", "branch", "--show-current")])

    def test_reports_mismatched_issue(self) -> None:
        responses = dict(RESPONSES)
        key = ("gh", "issue", "view", "102", "--json", "number,state")
        responses[key] = '{"number":103,"state":"OPEN"}'
        with self.assertRaisesRegex(WorkflowStatusError, "absent"):
            collect(lambda tool, *args: responses[(tool, *args)])

    def test_execute_uses_resolved_binary_without_a_shell(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="ok\n", stderr="")
        with (
            patch("scripts.workflow_status.shutil.which", return_value="/usr/bin/git"),
            patch("scripts.workflow_status.subprocess.run", return_value=completed) as run,
        ):
            self.assertEqual(execute("git", "status", "--short"), "ok")
        run.assert_called_once_with(
            ["/usr/bin/git", "status", "--short"], check=True, capture_output=True, text=True
        )

    def test_execute_and_main_report_failures(self) -> None:
        with (
            patch("scripts.workflow_status.shutil.which", return_value=None),
            self.assertRaisesRegex(WorkflowStatusError, "unavailable"),
        ):
            execute("gh", "issue")
        with patch("scripts.workflow_status.collect", side_effect=WorkflowStatusError("offline")):
            self.assertEqual(main(), 1)

    def test_deterministic_efficiency_proxy(self) -> None:
        status = collect(query)
        separate_transcript = json.dumps(
            [{"command": command, "output": output} for command, output in RESPONSES.items()],
            separators=(",", ":"),
        )
        self.assertEqual(len(RESPONSES), 6)
        self.assertLess(len(encode(status).encode()), len(separate_transcript.encode()))
