# Synthetic extractor workloads

These fixtures contain invented sessions only. They must not contain copied
transcripts, credentials, or private repository content.

The characterization suite assigns each fixture a stable workload role:

- `empty_session.jsonl`: smallest valid Claude-shaped session;
- `codex_session.jsonl`: Codex normalization and tool correlation;
- `large_arc_session.jsonl`: long conversation arc with redirects;
- `full_session.jsonl`: tool-heavy Claude session and complete output schema;
- `compacted_session.jsonl`: compacted context and large cache usage;
- `tool_results_only.jsonl`: orphaned tool-result edge case;
- `user_list_content.jsonl`: mixed text and tool-result content.

`test_extract_characterization.py` hashes canonical JSON output for the five
representative workloads. A digest change is a compatibility event: update it
only after reviewing the corresponding schema or behavior change.

Malformed-input and bounded-read cases are generated in temporary directories
by the tests so large or invalid artifacts are not committed.
