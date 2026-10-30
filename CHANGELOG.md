# Changelog

## v0.2.0 - 2026-10-30 (continued)

- The PyPI project is `tokentracker-ai`, not `tokentracker`: PyPI rejects a new
  project whose name is too close to an existing one (`token-tracker` exists).
  The distribution, import and command stay `tokentracker`, so install with
  `pipx install tokentracker-ai` and run `tokentracker`.

## v0.2.0 - 2026-10-30

- Renamed from tokenwatch to tokentracker: the PyPI name `tokenwatch` belongs
  to another project, and `token-tracker` is taken by a tool with the same
  pitch. The command, import and distribution are all `tokentracker` now.
- Nothing else changed; no behaviour differences.

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
