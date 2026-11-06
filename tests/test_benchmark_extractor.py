import json
import subprocess
import sys
from pathlib import Path

from scripts.benchmark_extractor import benchmark_suite, targets_met


def test_benchmark_suite_covers_synthetic_workloads() -> None:
    report = benchmark_suite(Path("tests/fixtures"), repeats=1, startup_repeats=1)

    assert list(report["workloads"]) == ["small", "large", "tool-heavy", "compacted"]
    assert all(item["input_bytes"] > 0 for item in report["workloads"].values())
    assert all(item["peak_traced_mib"] > 0 for item in report["workloads"].values())
    assert report["startup_ms"] > 0
    assert all(targets_met(report).values())


def test_benchmark_cli_emits_json() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/benchmark_extractor.py", "--repeats", "1"],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(completed.stdout)
    assert report["target_status"] == targets_met(report)
