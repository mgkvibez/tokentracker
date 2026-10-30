import json

from tokenwatch.attribute import analyse
from tokenwatch.records import Event
from tokenwatch.report import render_dashboard, render_json, render_text
from tokenwatch.usage import Usage

EVENTS = [
    Event(session="sess-a", model="claude-sonnet-4-5", usage=Usage(input=8000, output=100),
          files=["src/big.py"], skill="threat-model"),
    Event(session="sess-b", model="claude-sonnet-4-5", usage=Usage(input=200, output=50)),
]


def test_text_report_names_the_expensive_target_with_its_share():
    text = render_text(analyse(EVENTS))
    assert "src/big.py" in text and "skill:threat-model" in text
    assert "the expensive one" in text          # >= 40% of spend


def test_text_report_marks_missing_prices_instead_of_inventing_them():
    text = render_text(analyse([Event(model="mystery", usage=Usage(input=10))]))
    assert "cost: unavailable" in text


def test_text_report_says_so_when_there_is_nothing_to_show():
    assert "no model calls" in render_text(analyse([]))


def test_json_report_is_parseable_and_complete():
    payload = json.loads(render_json(analyse(EVENTS)))
    assert payload["events"] == 2
    assert payload["tokens"]["total"] == 8350
    assert payload["sessions"]["sess-a"]["tokens"] == 8100
    assert abs(sum(t["share_pct"] for t in payload["targets"]) - 100.0) < 0.2


def test_dashboard_frame_clears_the_screen_and_fits_a_terminal():
    frame = render_dashboard(analyse(EVENTS))
    assert frame.startswith("\033[2J")
    assert "tokenwatch" in frame
