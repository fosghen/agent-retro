"""Reproducible extractor benchmark over synthetic repository fixtures."""

import contextlib
import io
import math
import statistics
import time
import tracemalloc
from pathlib import Path

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
