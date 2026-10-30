import json

from tokenwatch.cli import main

FIXTURES = "tests/fixtures"


def test_report_on_fixtures_returns_zero(capsys):
    assert main(["report", FIXTURES]) == 0
    out = capsys.readouterr().out
    assert "Where the context went" in out
    assert "src/parser.py" in out


def test_report_json_is_machine_readable(capsys):
    assert main(["report", FIXTURES, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["events"] == 6
    assert payload["tokens"]["total"] > 0


def test_empty_directory_exits_nonzero_with_a_clear_message(tmp_path, capsys):
    assert main(["report", str(tmp_path)]) == 1
    assert "no model calls" in capsys.readouterr().out


def test_prices_lists_the_table_and_its_as_of_stamp(capsys):
    assert main(["prices"]) == 0
    out = capsys.readouterr().out
    assert "as of" in out and "claude-sonnet-4-5" in out


def test_version_flag_is_available():
    import pytest
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
