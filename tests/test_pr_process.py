import unittest
from unittest.mock import patch

from scripts.check_pr_process import ProcessDeclarationError, check, main

TRIGGERS = """\
- [ ] data migration or persisted-schema change
- [ ] concurrency, locking, or transaction-boundary change
- [ ] privacy, security, authentication, or authorization change
- [ ] destructive operation or external side effect
- [ ] unresolved correctness uncertainty after self-review
- [ ] explicit user request for independent review
"""
BRANCH = "feature/issue-94-workflow"
ISSUE = "Closes #94\n"


def declaration(
    *,
    risk: str = "low",
    review: str = "not-used",
    provider: str = "none",
    usage: str = "not-applicable",
    effects: str = "none",
) -> str:
    return (
        f"{ISSUE}Risk: {risk}\nIndependent review: {review}\n"
        f"Review provider: {provider}\nModel review usage: {usage}\n"
        f"External effects: {effects}\n"
    )


class PullRequestProcessTests(unittest.TestCase):
    def test_low_risk_skips_independent_review(self) -> None:
        check(f"{declaration()}{TRIGGERS}", BRANCH)

    def test_high_risk_requires_trigger_and_completed_review(self) -> None:
        body = TRIGGERS.replace("- [ ] concurrency", "- [x] concurrency")
        declared = declaration(risk="high", review="completed", provider="human")
        check(f"{declared}{body}", BRANCH)

    def test_model_review_requires_truthful_usage(self) -> None:
        body = TRIGGERS.replace("- [ ] explicit user", "- [x] explicit user")
        for usage in ("unavailable", "tokens=1200; cost=USD 0.42"):
            declared = declaration(
                risk="high",
                review="completed",
                provider="model",
                usage=usage,
            )
            check(f"{declared}{body}", BRANCH)

    def test_rejects_unreported_model_usage(self) -> None:
        body = TRIGGERS.replace("- [ ] concurrency", "- [x] concurrency")
        declared = declaration(risk="high", review="completed", provider="model")
        with self.assertRaisesRegex(ProcessDeclarationError, "model review usage"):
            check(f"{declared}{body}", BRANCH)

    def test_rejects_unnecessary_low_risk_review(self) -> None:
        declared = declaration(review="completed", provider="human")
        with self.assertRaisesRegex(ProcessDeclarationError, "low-risk"):
            check(f"{declared}{TRIGGERS}", BRANCH)

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

    def test_local_preflight_reads_explicit_body_file(self) -> None:
        body = f"{declaration()}{TRIGGERS}"
        with patch("pathlib.Path.read_text", return_value=body) as read:
            result = main(["--body-file", "pr.md", "--branch", BRANCH])
        self.assertEqual(result, 0)
        read.assert_called_once_with()
