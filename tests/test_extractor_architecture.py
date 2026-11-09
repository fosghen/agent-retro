"""Executable examples for extractor import boundaries."""

from pathlib import Path

from scripts.check_extractor_architecture import violations

ROOT = Path(__file__).resolve().parents[1]


def package(tmp_path: Path, modules: dict[str, str]) -> Path:
    """Create one minimal transcript package fixture."""
    root = tmp_path / "agent_retro"
    root.mkdir()
    for name, source in modules.items():
        (root / f"transcript_{name}.py").write_text(source)
    return root


def test_live_extractor_respects_declared_boundaries() -> None:
    assert violations(ROOT / "src/agent_retro") == []


def test_allowed_lower_level_import_passes(tmp_path: Path) -> None:
    root = package(
        tmp_path,
        {
            "io": "type JSONRecord = dict[str, object]\n",
            "metadata": "from agent_retro.transcript_io import JSONRecord\n",
        },
    )

    assert violations(root) == []


def test_projection_cannot_import_composition_root(tmp_path: Path) -> None:
    root = package(
        tmp_path,
        {"conversation": "from agent_retro.transcript_result import extract_transcript\n"},
    )

    assert violations(root) == [
        (
            "transcript_conversation -> transcript_result violates projection boundary; "
            "depend toward io/metadata, not result"
        )
    ]


def test_package_cannot_import_compatibility_cli(tmp_path: Path) -> None:
    root = package(tmp_path, {"io": "from scripts.extract import extract_all_streaming\n"})

    assert violations(root) == [
        (
            "transcript_io -> scripts.extract violates CLI boundary; "
            "move shared behavior into agent_retro"
        )
    ]


def test_cycle_names_both_modules(tmp_path: Path) -> None:
    root = package(
        tmp_path,
        {
            "io": "from agent_retro.transcript_metadata import parse_timestamp\n",
            "metadata": "from agent_retro.transcript_io import JSONRecord\n",
        },
    )

    assert (
        "cycle: transcript_io -> transcript_metadata -> transcript_io; remove the upward import"
        in violations(root)
    )
