from tokenwatch.adapters import iter_files, load_events, parse_claude_code, parse_generic, parse_line

FIXTURES = "tests/fixtures"


def test_claude_code_line_keeps_model_usage_and_file():
    line = '{"type":"assistant","sessionId":"s1","message":{"model":"claude-sonnet-4-5","usage":{"input_tokens":10,"output_tokens":5},"content":[{"type":"tool_use","name":"Read","input":{"file_path":"a.py"}}]}}'
    event = parse_line(line)
    assert event.model == "claude-sonnet-4-5"
    assert event.usage.input == 10 and event.usage.output == 5
    assert event.files == ["a.py"]
    assert event.session == "s1"


def test_skill_invocation_is_captured():
    line = '{"type":"assistant","message":{"model":"m","usage":{"input_tokens":1},"content":[{"type":"tool_use","name":"Skill","input":{"skill":"triage-alert"}}]}}'
    assert parse_line(line).skill == "triage-alert"


def test_slash_command_counts_as_a_skill_without_the_slash():
    line = '{"type":"assistant","message":{"model":"m","usage":{"input_tokens":1},"content":[{"type":"tool_use","name":"SlashCommand","input":{"command":"/cve-research"}}]}}'
    assert parse_line(line).skill == "cve-research"


def test_generic_openai_shape_is_understood():
    event = parse_generic({"model": "gpt-5", "usage": {"prompt_tokens": 7, "completion_tokens": 3}})
    assert event.usage.input == 7 and event.usage.output == 3


def test_user_lines_and_garbage_are_skipped():
    assert parse_line('{"type":"user","message":{"content":"hi"}}') is None
    assert parse_line("not json at all") is None
    assert parse_line("") is None


def test_directory_load_picks_up_both_harness_shapes():
    events = load_events([FIXTURES])
    sources = {e.source for e in events}
    assert sources == {"claude-code", "generic"}
    assert len(events) == 6


def test_zero_token_lines_do_not_pollute_totals():
    for event in load_events([FIXTURES]):
        assert event.usage.total > 0


def test_iter_files_ignores_non_log_suffixes(tmp_path):
    (tmp_path / "keep.jsonl").write_text("{}\n")
    (tmp_path / "skip.txt").write_text("nope")
    found = [p.name for p in iter_files([str(tmp_path)])]
    assert found == ["keep.jsonl"]
