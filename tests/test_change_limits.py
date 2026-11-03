import unittest

from scripts.check_change_limits import ChangeLimitError, check, count_lines


class ChangeLimitTests(unittest.TestCase):
    def test_accepts_boundaries(self) -> None:
        check("feature/issue-94-topic", {str(index): "25\t25\tfile.py" for index in range(5)})

    def test_rejects_large_commit(self) -> None:
        with self.assertRaisesRegex(ChangeLimitError, "51 changed lines"):
            check("feature/issue-94-topic", {"large": "51\t0\tfile.py"})

    def test_rejects_large_pull_request(self) -> None:
        commits = {str(index): "50\t1\tfile.py" for index in range(5)}
        with self.assertRaisesRegex(ChangeLimitError, "255 changed lines"):
            check("feature/issue-94-topic", commits)

    def test_rejects_six_commits(self) -> None:
        with self.assertRaisesRegex(ChangeLimitError, "6 commits"):
            check("feature/issue-94-topic", {str(index): "" for index in range(6)})

    def test_rejects_branch_without_issue(self) -> None:
        with self.assertRaisesRegex(ChangeLimitError, "issue-N"):
            check("feature/topic", {})

    def test_rejects_protected_branch(self) -> None:
        for branch in ("main", "master"):
            with self.subTest(branch=branch), self.assertRaises(ChangeLimitError):
                check(branch, {})

    def test_rejects_binary_change(self) -> None:
        with self.assertRaisesRegex(ChangeLimitError, "binary"):
            count_lines("-\t-\tasset.bin")

    def test_only_generated_root_lock_is_excluded(self) -> None:
        self.assertEqual(count_lines("500\t500\tuv.lock"), 0)
        with self.assertRaises(ChangeLimitError):
            check("feature/issue-94-topic", {"large": "51\t0\tnested/uv.lock"})
        with self.assertRaises(ChangeLimitError):
            count_lines("-\t-\tuv.lock")


if __name__ == "__main__":
    unittest.main()
