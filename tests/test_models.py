import json
import unittest
from pathlib import Path

from agent_retro.models import ProposalStatus, SchemaError, proposal_from_mapping

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


if __name__ == "__main__":
    unittest.main()
