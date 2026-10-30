import json

from tokenwatch.proxy import append_record, usage_from_body
from tokenwatch.usage import Usage


def test_anthropic_usage_block_is_parsed():
    body = json.dumps({"model": "claude-sonnet-4-5",
                       "usage": {"input_tokens": 12, "output_tokens": 4,
                                 "cache_read_input_tokens": 30, "cache_creation_input_tokens": 5}}).encode()
    usage, model = usage_from_body(body)
    assert (usage.input, usage.output, usage.cache_read, usage.cache_write) == (12, 4, 30, 5)
    assert model == "claude-sonnet-4-5"


def test_openai_usage_block_is_parsed():
    body = json.dumps({"model": "gpt-5", "usage": {"prompt_tokens": 9, "completion_tokens": 2}}).encode()
    usage, model = usage_from_body(body)
    assert (usage.input, usage.output) == (9, 2)
    assert model == "gpt-5"


def test_non_json_or_absent_usage_yields_nothing():
    assert usage_from_body(b"<html>oops</html>") == (None, "")
    assert usage_from_body(json.dumps({"ok": True}).encode()) == (None, "")
    assert usage_from_body(json.dumps({"usage": {"input_tokens": 0, "output_tokens": 0}}).encode()) == (None, "")


def test_record_is_written_in_the_shape_the_generic_adapter_reads(tmp_path):
    from tokenwatch.adapters import parse_line
    log = tmp_path / "logs" / "proxy.jsonl"
    append_record(log, "claude-sonnet-4-5", Usage(input=5, output=2), "/v1/messages")
    line = log.read_text().splitlines()[0]
    event = parse_line(line)
    assert event.usage.input == 5 and event.usage.output == 2
    assert event.model == "claude-sonnet-4-5"
    assert event.session == "logs"
