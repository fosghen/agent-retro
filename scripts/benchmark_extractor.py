"""Reproducible extractor benchmark over synthetic repository fixtures."""

import argparse
import contextlib
import io
import json
import math
import statistics
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

from agent_retro.transcript_result import extract_transcript

MIB = 1024 * 1024
WORKLOADS = {
    "small": "empty_session.jsonl",
    "large": "large_arc_session.jsonl",
    "tool-heavy": "full_session.jsonl",
    "compacted": "compacted_session.jsonl",
}
TARGETS = {
    "minimum_throughput_mib_s": 0.5,
    "maximum_peak_traced_mib": 2.0,
    "maximum_startup_ms": 100.0,
}


def _extract_quietly(path: Path) -> None:
    with contextlib.redirect_stderr(io.StringIO()):
        extract_transcript(path, summary=True)


def _workload_metrics(path: Path, repeats: int) -> dict[str, float | int]:
    size = path.stat().st_size
    iterations = max(1, math.ceil(MIB / size))
    elapsed_samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        for _ in range(iterations):
            _extract_quietly(path)
        elapsed_samples.append(time.perf_counter() - started)

    tracemalloc.start()
    _extract_quietly(path)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = statistics.median(elapsed_samples)
    return {
        "input_bytes": size,
        "iterations": iterations,
        "throughput_mib_s": round((size * iterations / MIB) / elapsed, 3),
        "peak_traced_mib": round(peak / MIB, 3),
    }


def _startup_ms(repeats: int) -> float:
    command = [sys.executable, "-c", "import agent_retro.transcript_result"]
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        subprocess.run(command, check=True)  # noqa: S603
        samples.append((time.perf_counter() - started) * 1000)
    return round(statistics.median(samples), 3)


def targets_met(report: dict[str, Any]) -> dict[str, bool]:
    """Evaluate the published benchmark targets against one report."""
    workloads = report["workloads"].values()
    return {
        "throughput": min(item["throughput_mib_s"] for item in workloads)
        >= TARGETS["minimum_throughput_mib_s"],
        "peak_memory": max(item["peak_traced_mib"] for item in workloads)
        <= TARGETS["maximum_peak_traced_mib"],
        "startup": report["startup_ms"] <= TARGETS["maximum_startup_ms"],
    }


def benchmark_suite(
    fixtures: Path, *, repeats: int = 5, startup_repeats: int = 5
) -> dict[str, Any]:
    """Measure fixed synthetic workloads and return a stable JSON-ready report."""
    workloads = {
        name: _workload_metrics(fixtures / filename, repeats)
        for name, filename in WORKLOADS.items()
    }
    return {
        "method": "median wall time; tracemalloc peak; isolated import startup",
        "repeats": repeats,
        "startup_repeats": startup_repeats,
        "workloads": workloads,
        "startup_ms": _startup_ms(startup_repeats),
        "targets": TARGETS,
    }


def main() -> None:
    """Run the benchmark CLI and emit its JSON report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=Path("tests/fixtures"))
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--startup-repeats", type=int, default=5)
    args = parser.parse_args()
    if min(args.repeats, args.startup_repeats) < 1:
        parser.error("repeat counts must be positive")
    report = benchmark_suite(
        args.fixtures, repeats=args.repeats, startup_repeats=args.startup_repeats
    )
    report["target_status"] = targets_met(report)
    sys.stdout.write(f"{json.dumps(report, indent=2, sort_keys=True)}\n")


if __name__ == "__main__":
    main()
