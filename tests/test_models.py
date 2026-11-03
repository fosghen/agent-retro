import json
import unittest
from pathlib import Path

from agent_retro.models import (
    EvidenceReference,
    ProposalObservation,
    ProposalStatus,
    SchemaError,
    proposal_from_mapping,
)

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ProposalModelTests(unittest.TestCase):
    def test_valid_fixture_builds_typed_model(self) -> None:
        proposal = proposal_from_mapping(fixture("proposal_valid.json"))

        self.assertEqual(proposal.status, ProposalStatus.NEW)
        self.assertEqual(proposal.revision.evidence[0].source_hash, "sha256:abc")

    def test_invalid_fixture_has_validation_error(self) -> None:
        with self.assertRaises(SchemaError):
            proposal_from_mapping(fixture("proposal_invalid.json"))

    def test_forward_schema_is_rejected(self) -> None:
        with self.assertRaisesRegex(SchemaError, "unsupported schema version"):
            proposal_from_mapping(fixture("proposal_forward.json"))

    def test_invalid_status_transition_is_rejected(self) -> None:
        proposal = proposal_from_mapping(fixture("proposal_valid.json"))

        with self.assertRaises(SchemaError):
            proposal.transition(ProposalStatus.IMPLEMENTED)

    def test_review_fields_are_validated_and_backward_compatible(self) -> None:
        raw = fixture("proposal_valid.json")
        self.assertIsInstance(raw, dict)
        raw["revision"]["problem"] = "Repeated failures"
        proposal = proposal_from_mapping(raw)

        self.assertEqual(proposal.revision.problem, "Repeated failures")
        self.assertEqual(proposal.revision.validation, "Not recorded")

    def test_observation_fingerprint_normalizes_case_and_whitespace(self) -> None:
        first = ProposalObservation(
            " Improve   review ", "Agent Retro", " One file ", EvidenceReference("a", "one")
        )
        second = ProposalObservation(
            "improve review", "agent retro", "one  file", EvidenceReference("b", "two")
        )
        punctuated = ProposalObservation(
            "improve-review", "agent retro", "one file", EvidenceReference("c", "three")
        )

        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertNotEqual(first.fingerprint, punctuated.fingerprint)

    def test_material_scope_changes_observation_fingerprint(self) -> None:
        first = ProposalObservation("improve", "retro", "one file", EvidenceReference("a", "one"))
        second = ProposalObservation("improve", "retro", "two files", EvidenceReference("b", "two"))

        self.assertNotEqual(first.fingerprint, second.fingerprint)

    def test_observation_rejects_unbounded_evidence(self) -> None:
        with self.assertRaisesRegex(SchemaError, "source_hash"):
            ProposalObservation("intent", "target", "scope", EvidenceReference("x" * 129, "ok"))
        with self.assertRaisesRegex(SchemaError, "excerpt"):
            ProposalObservation("intent", "target", "scope", EvidenceReference("x", "y" * 501))


if __name__ == "__main__":
    unittest.main()
