"""Reproducible extractor benchmark over synthetic repository fixtures."""

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
