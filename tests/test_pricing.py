import json
import pathlib

import pytest

from tokentracker.pricing import cost, load_prices, match_price
from tokentracker.usage import Usage

PRICES = load_prices()


def test_cost_uses_input_and_output_rates():
    # sonnet: $3/M in, $15/M out
    assert cost(Usage(input=1_000_000), "claude-sonnet-4-5", PRICES) == pytest.approx(3.0)
    assert cost(Usage(output=1_000_000), "claude-sonnet-4-5", PRICES) == pytest.approx(15.0)


def test_cache_read_is_discounted_and_cache_write_is_not_free():
    read = cost(Usage(cache_read=1_000_000), "claude-sonnet-4-5", PRICES)
    write = cost(Usage(cache_write=1_000_000), "claude-sonnet-4-5", PRICES)
    assert read == pytest.approx(0.3)
    assert write == pytest.approx(3.75)
    assert read < write


def test_unknown_model_has_no_price():
    assert cost(Usage(input=1000), "mystery-model", PRICES) is None
    assert match_price("", PRICES) is None


def test_longest_prefix_wins_so_dated_versions_resolve():
    prices = {"claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
              "claude-sonnet-4-5-20260101": {"input": 2.0, "output": 10.0}}
    assert match_price("claude-sonnet-4-5-20260101", prices)["input"] == 2.0


def test_price_file_overrides_defaults(tmp_path):
    path = tmp_path / "prices.json"
    path.write_text(json.dumps({"prices": {"my-model": {"input": 1, "output": 2}}}))
    prices = load_prices(str(path))
    assert list(prices) == ["my-model"]
    assert cost(Usage(input=1_000_000), "my-model", prices) == pytest.approx(1.0)


def test_price_file_entry_without_rates_is_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"prices": {"my-model": {"input": 1}}}))
    with pytest.raises(ValueError):
        load_prices(str(path))
