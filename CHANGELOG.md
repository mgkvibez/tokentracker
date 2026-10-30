# Changelog

## v0.1.0 - 2026-10-30

- `tokenwatch report <paths>`: totals, estimated cost, ranked context eaters with
  percentages, and a per-session breakdown.
- `tokenwatch watch <paths>`: the same numbers redrawn in place for live work.
- `tokenwatch proxy`: pass-through proxy that records each response's usage to
  JSONL for harnesses that keep no logs. Streamed responses are forwarded but
  not counted, and the README says so.
- Adapters for Claude Code session JSONL and any flat JSONL with a `usage` block.
- Attribution splits a call evenly across the files and skills it touched, with an
  explicit `(unattributed)` bucket, so shares always total 100%.
- Prices are a dated data table with `--prices` override; an unknown model renders
  `cost: unavailable` rather than a guessed figure.
- 37 tests, `scripts/verify.sh` gate, CI on Python 3.9 and 3.12.
