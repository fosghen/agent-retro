"""Contract for the privacy-safe Agent Retro skill evaluation corpus."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = {"positive", "negative", "boundary", "artifact"}
MINIMUM_CASES = 5
MAXIMUM_CASES = 10


def corpus() -> list[dict[str, object]]:
    """Load the versioned deterministic evaluation inputs."""
    value = json.loads((ROOT / "evaluations/corpus.json").read_text())
    assert value["schema_version"] == 1
    return value["cases"]


def test_corpus_has_representative_unique_cases() -> None:
    cases = corpus()

    assert MINIMUM_CASES <= len(cases) <= MAXIMUM_CASES
    assert len({case["id"] for case in cases}) == len(cases)
    assert {case["kind"] for case in cases} == KINDS


def test_each_case_has_deterministic_grading_inputs() -> None:
    for case in corpus():
        assert set(case) == {
            "id",
            "kind",
            "prompt",
            "trigger",
            "required_steps",
            "forbidden_actions",
            "expected_artifacts",
        }
        assert isinstance(case["trigger"], bool)
        for field in ("required_steps", "forbidden_actions", "expected_artifacts"):
            assert isinstance(case[field], list)
        assert case["prompt"]


def test_corpus_contains_only_synthetic_context() -> None:
    serialized = json.dumps(corpus()).lower()

    assert "/users/" not in serialized
    assert "password" not in serialized
    assert "token=" not in serialized
