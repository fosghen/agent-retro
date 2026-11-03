import unittest

from scripts.check_pr_process import ProcessDeclarationError, check

TRIGGERS = """\
- [ ] data migration or persisted-schema change
- [ ] concurrency, locking, or transaction-boundary change
- [ ] privacy, security, authentication, or authorization change
- [ ] destructive operation or external side effect
- [ ] unresolved correctness uncertainty after self-review
"""
BRANCH = "feature/issue-94-workflow"
ISSUE = "Closes #94\n"


class PullRequestProcessTests(unittest.TestCase):
    def test_low_risk_skips_independent_review(self) -> None:
        check(f"{ISSUE}Risk: low\nIndependent review: not-used\n{TRIGGERS}", BRANCH)

    def test_high_risk_requires_trigger_and_completed_review(self) -> None:
        body = TRIGGERS.replace("- [ ] concurrency", "- [x] concurrency")
        check(f"{ISSUE}Risk: high\nIndependent review: completed\n{body}", BRANCH)

    def test_rejects_unnecessary_low_risk_review(self) -> None:
        with self.assertRaisesRegex(ProcessDeclarationError, "low-risk"):
            check(f"{ISSUE}Risk: low\nIndependent review: completed\n{TRIGGERS}", BRANCH)

    def test_rejects_high_risk_without_review_or_trigger(self) -> None:
        invalid = (
            f"{ISSUE}Risk: high\nIndependent review: not-used\n{TRIGGERS}",
            f"{ISSUE}Risk: high\nIndependent review: completed\n{TRIGGERS}",
        )
        for body in invalid:
            with self.subTest(body=body), self.assertRaises(ProcessDeclarationError):
                check(body, BRANCH)

    def test_rejects_missing_or_duplicate_declarations(self) -> None:
        invalid = (
            "",
            f"{ISSUE}Risk: low\nRisk: high\nIndependent review: not-used",
            f"{ISSUE}Risk: low\nIndependent review: not-used\nIndependent review: completed",
        )
        for body in invalid:
            with self.subTest(body=body), self.assertRaises(ProcessDeclarationError):
                check(body, BRANCH)

    def test_rejects_missing_or_mismatched_issue(self) -> None:
        body = f"{ISSUE}Risk: low\nIndependent review: not-used\n{TRIGGERS}"
        for branch in ("feature/topic", "feature/issue-95-topic"):
            with (
                self.subTest(branch=branch),
                self.assertRaisesRegex(ProcessDeclarationError, "Closes"),
            ):
                check(body, branch)
