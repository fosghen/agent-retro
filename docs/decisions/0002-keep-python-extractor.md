# ADR 0002: Keep the transcript extractor in Python

- Status: accepted
- Date: 2026-11-06
- Issue: #135

## Context
The decomposed streaming extractor could remain Python, move hot paths to Rust,
or be replaced by Rust. Agent Retro is a local interactive tool, so the useful
limits are startup latency, throughput on every representative workload, and
bounded peak memory. The committed fixtures are synthetic and cover small,
large, tool-heavy, and compacted transcripts.

The regression targets are at least 0.5 MiB/s input throughput for every
workload, at most 2 MiB traced peak allocations, and at most 100 ms for a fresh
interpreter to import the extractor. These limits favor responsive local use
and leave headroom for slower development machines. Peak memory intentionally
uses `tracemalloc`, making the Python allocation measurement portable; it does
not claim to measure interpreter or native-library RSS.

## Measurement
From the repository root on an Apple Silicon Mac with Python 3.12.14:

```sh
uv run --frozen --no-sync python scripts/benchmark_extractor.py
```

The five-repeat median benchmark measured:
| Workload | Input | Throughput (MiB/s) | Peak traced (MiB) |
|---|---:|---:|---:|
| small | 166 B | 0.769 | 0.016 |
| large | 4,953 B | 18.418 | 0.026 |
| tool-heavy | 10,376 B | 33.777 | 0.038 |
| compacted | 3,392 B | 13.485 | 0.020 |

Median isolated import startup was 37.791 ms. The script batches each fixture
to at least 1 MiB of input per timing sample, reports the fixed targets beside
the measurements, and evaluates all three limits.

## Decision
Keep the extractor in Python. Every target passes, peak allocations are tiny,
and larger inputs already process much faster than the small-file worst case.
A hybrid or Rust implementation would add build and packaging complexity
without evidence of a user-visible bottleneck.
Do not open a Rust implementation issue. Reconsider only if this benchmark
misses a target or a real workload exposes a metric the suite omits.
