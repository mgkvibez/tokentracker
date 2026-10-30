"""Model prices, kept in data not code.

Defaults are editable starting points, not gospel: providers change prices and
`tokenwatch` never calls out to find out. Pass `--prices file.json` to replace
them, and check the `as_of` stamp before trusting any dollar figure.
"""

from __future__ import annotations

import json
import pathlib
from typing import Dict, Optional

from .usage import Usage

AS_OF = "2026-10"

# USD per million tokens. cache_read is charged at a discount on the input
# rate and cache_write at a premium; both are expressed as multipliers so a
# price update is one number, not three.
DEFAULT_PRICES: Dict[str, Dict[str, float]] = {
    "claude-opus-4-1": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    "gpt-5": {"input": 1.25, "output": 10.0},
    "gpt-5-mini": {"input": 0.25, "output": 2.0},
    "o4-mini": {"input": 1.1, "output": 4.4},
}
CACHE_READ_MULTIPLIER = 0.1
CACHE_WRITE_MULTIPLIER = 1.25


def load_prices(path: Optional[str] = None) -> Dict[str, Dict[str, float]]:
    """Built-in table, optionally replaced wholesale by a JSON file."""
    if not path:
        return dict(DEFAULT_PRICES)
    data = json.loads(pathlib.Path(path).read_text())
    prices = data.get("prices", data)
    out: Dict[str, Dict[str, float]] = {}
    for model, rates in prices.items():
        if not isinstance(rates, dict) or "input" not in rates or "output" not in rates:
            raise ValueError(f"price entry for {model!r} needs input and output rates")
        out[str(model)] = {"input": float(rates["input"]), "output": float(rates["output"])}
    return out


def match_price(model: str, prices: Dict[str, Dict[str, float]]) -> Optional[Dict[str, float]]:
    """Exact match, then longest prefix match so version suffixes still resolve."""
    if not model:
        return None
    if model in prices:
        return prices[model]
    candidates = [k for k in prices if model.startswith(k)]
    if not candidates:
        return None
    return prices[max(candidates, key=len)]


def cost(usage: Usage, model: str, prices: Dict[str, Dict[str, float]]) -> Optional[float]:
    """USD for one call, or None when the model has no known price."""
    rates = match_price(model, prices)
    if rates is None:
        return None
    per_in = rates["input"] / 1_000_000
    per_out = rates["output"] / 1_000_000
    return (
        usage.input * per_in
        + usage.cache_read * per_in * CACHE_READ_MULTIPLIER
        + usage.cache_write * per_in * CACHE_WRITE_MULTIPLIER
        + usage.output * per_out
    )
