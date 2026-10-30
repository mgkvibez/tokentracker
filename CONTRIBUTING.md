# Contributing

Small, honest, tested. That is the whole standard.

## The gate

```bash
python3 -m pip install -e ".[dev]"
bash scripts/verify.sh
```

Four checks run locally and again in CI on 3.9 and 3.12: editable install, version consistency (`pyproject.toml` must equal `tokenwatch.__version__`), the test suite, and a CLI smoke test that must exit 0 and print a report.

## Adding a harness adapter

1. Add a `parse_<harness>(obj) -> Event | None` function in `tokenwatch/adapters.py`, and register it in `ADAPTERS`.
2. Return `None` for any line that is not yours, so the next adapter gets a turn.
3. Add a **real** log excerpt to `tests/fixtures/`. Do not hand-write the shape you think the harness emits; take a line from an actual session, redact paths if needed.
4. Add one test asserting session, model and usage for that fixture, and one asserting a malformed line returns `None`.

## Changing prices

Prices are data. Update the table in `tokenwatch/pricing.py` and bump `AS_OF`, or ship a `prices.json` and pass `--prices`. Never invent a price for a model you cannot verify: an unknown model must render `cost: unavailable`.

## What gets rejected

- A cost figure calculated from a guessed or stale price without a stated `as_of`.
- Attribution that silently drops tokens instead of using `(unattributed)`.
- A new runtime dependency. This tool installs with `pip` and nothing else.
- Tests that assert on our own formatting strings instead of the numbers behind them.
