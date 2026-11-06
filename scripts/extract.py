#!/usr/bin/env python3
"""
Extract structured data from a Claude Code session transcript (JSONL).

Usage:
    python extract.py <session-jsonl-path> [--subagents-dir <path>] [--summary] [--metadata-only]

Outputs JSON to stdout. Use --summary for a compact version that omits
individual tool call details (just counts and key events).
Use --metadata-only for cheap session verification (head/tail read only).
"""

import json
import sys
from pathlib import Path

from agent_retro.transcript_aggregate import PRICING_LAST_VERIFIED
from agent_retro.transcript_io import (
    LITE_READ_BUF_SIZE,
    detect_transcript_format,
    read_head_tail,
    stream_raw_jsonl,
)
from agent_retro.transcript_metadata import (
    extract_json_field,
    extract_metadata_lite as _typed_metadata_lite,
)
from agent_retro.transcript_result import extract_transcript


def extract_metadata_lite(path):
    """Extract bounded session metadata through the typed compatibility boundary."""
    return _typed_metadata_lite(path)


def extract_all_streaming(jsonl_path, subagents_dir=None, summary_mode=False):
    """Delegate the legacy API to the typed extraction entry point."""
    return extract_transcript(jsonl_path, subagents_dir=subagents_dir, summary=summary_mode)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract.py <session.jsonl> [--subagents-dir <path>] [--summary] [--metadata-only]")
        sys.exit(1)

    jsonl_path = sys.argv[1]
    subagents_dir = None
    summary_mode = "--summary" in sys.argv
    metadata_only = "--metadata-only" in sys.argv

    if metadata_only:
        result = extract_metadata_lite(jsonl_path)
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)

    if "--subagents-dir" in sys.argv:
        idx = sys.argv.index("--subagents-dir")
        if idx + 1 < len(sys.argv):
            subagents_dir = sys.argv[idx + 1]
    else:
        # Auto-detect: look for sibling directory with same name as the JSONL
        stem = Path(jsonl_path).stem
        candidate = Path(jsonl_path).parent / stem / "subagents"
        if candidate.is_dir():
            subagents_dir = str(candidate)

    result = extract_all_streaming(jsonl_path, subagents_dir, summary_mode)
    print(json.dumps(result, indent=2, default=str))
