import pytest

from tokenwatch.attribute import UNATTRIBUTED, _split, analyse
from tokenwatch.records import Event
from tokenwatch.usage import Usage


def _event(**kw):
    base = dict(session="s1", model="claude-sonnet-4-5", usage=Usage(input=100, output=20))
    base.update(kw)
    return Event(**base)


def test_split_keeps_every_token_and_gives_remainder_to_the_first_part():
    parts = _split(Usage(input=100, output=7, cache_read=5, cache_write=3), 3)
    assert sum(p.input for p in parts) == 100
    assert sum(p.output for p in parts) == 7
    assert sum(p.cache_read for p in parts) == 5
    assert sum(p.cache_write for p in parts) == 3
    assert parts[0].input == 34          # 33 + remainder 1


def test_split_of_zero_parts_is_empty():
    assert _split(Usage(input=5), 0) == []


def test_call_with_no_targets_goes_to_unattributed():
    analysis = analyse([_event()])
    assert UNATTRIBUTED in analysis.buckets
    assert analysis.share(UNATTRIBUTED) == pytest.approx(100.0)


def test_two_files_share_one_call_evenly():
    analysis = analyse([_event(files=["a.py", "b.py"], usage=Usage(input=100))])
    assert analysis.buckets["a.py"].input == 50
    assert analysis.buckets["b.py"].input == 50


def test_file_and_skill_split_the_same_call():
    analysis = analyse([_event(files=["a.py"], skill="threat-model", usage=Usage(input=100))])
    assert analysis.buckets["a.py"].input == 50
    assert analysis.buckets["skill:threat-model"].input == 50


def test_shares_always_sum_to_one_hundred_percent():
    events = [_event(files=["a.py"]), _event(), _event(files=["b.py", "c.py"], skill="x")]
    analysis = analyse(events)
    total = sum(analysis.share(name) for name in analysis.buckets)
    assert total == pytest.approx(100.0)


def test_session_totals_add_up_across_events():
    analysis = analyse([_event(session="a", usage=Usage(input=10)),
                        _event(session="a", usage=Usage(input=5)),
                        _event(session="b", usage=Usage(input=1))])
    assert analysis.sessions["a"].input == 15
    assert analysis.sessions["b"].input == 1
    assert analysis.total.input == 16


def test_unpriced_model_is_reported_and_excluded_from_cost():
    analysis = analyse([_event(model="claude-sonnet-4-5"), _event(model="mystery-9")])
    assert analysis.unpriced_models == ["mystery-9"]
    assert analysis.cost_usd is not None


def test_all_unpriced_models_means_no_cost_at_all():
    analysis = analyse([_event(model="mystery-9")])
    assert analysis.cost_usd is None
