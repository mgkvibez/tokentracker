"""Harness log adapters.

Kept deliberately thin: one function per log shape, tried in order, and a new
harness means a new function plus a fixture, not a refactor.
"""

from __future__ import annotations

import json
import pathlib
from typing import Dict, Iterable, List, Optional

from .records import Event
from .usage import Usage

FILE_TOOLS = {"Read", "Edit", "Write", "MultiEdit", "NotebookEdit", "read_file",
              "write_file", "edit_file", "str_replace_editor"}


def _usage_from(raw: Dict[str, object]) -> Usage:
    """Accept Anthropic and OpenAI-style usage keys."""
    def num(*keys: str) -> int:
        for k in keys:
            v = raw.get(k)
            if isinstance(v, (int, float)):
                return int(v)
        return 0
    return Usage(
        input=num("input_tokens", "prompt_tokens"),
        output=num("output_tokens", "completion_tokens"),
        cache_read=num("cache_read_input_tokens", "cached_tokens"),
        cache_write=num("cache_creation_input_tokens"),
    )


def parse_claude_code(obj: Dict[str, object]) -> Optional[Event]:
    """Claude Code session JSONL: one line per message."""
    msg = obj.get("message")
    if not isinstance(msg, dict) or obj.get("type") not in (None, "assistant"):
        return None
    usage_raw = msg.get("usage")
    if not isinstance(usage_raw, dict):
        return None
    files: List[str] = []
    skill = ""
    for block in msg.get("content") or []:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = str(block.get("name") or "")
        payload = block.get("input") or {}
        if not isinstance(payload, dict):
            continue
        if name in FILE_TOOLS:
            path = payload.get("file_path") or payload.get("path")
            if isinstance(path, str) and path:
                files.append(path)
        elif name == "Skill":
            s = payload.get("skill") or payload.get("command") or payload.get("name")
            if isinstance(s, str) and s:
                skill = s
        elif name == "SlashCommand":
            c = payload.get("command")
            if isinstance(c, str) and c:
                skill = c.lstrip("/")
    return Event(
        ts=str(obj.get("timestamp") or ""),
        session=str(obj.get("sessionId") or obj.get("session_id") or ""),
        model=str(msg.get("model") or ""),
        usage=_usage_from(usage_raw),
        files=files,
        skill=skill,
        source="claude-code",
    )


def parse_generic(obj: Dict[str, object]) -> Optional[Event]:
    """Flat JSONL: ts/session/model/usage plus optional file and skill."""
    usage_raw = obj.get("usage")
    if not isinstance(usage_raw, dict):
        return None
    files = obj.get("files") or ([obj["file"]] if isinstance(obj.get("file"), str) else [])
    return Event(
        ts=str(obj.get("ts") or obj.get("timestamp") or ""),
        session=str(obj.get("session") or obj.get("session_id") or ""),
        model=str(obj.get("model") or ""),
        usage=_usage_from(usage_raw),
        files=[str(f) for f in files if f],
        skill=str(obj.get("skill") or ""),
        source="generic",
    )


ADAPTERS = (parse_claude_code, parse_generic)


def parse_line(line: str) -> Optional[Event]:
    """Try each adapter against one log line."""
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except ValueError:
        return None
    if not isinstance(obj, dict):
        return None
    for adapter in ADAPTERS:
        event = adapter(obj)
        if event is not None:
            return event
    return None


def iter_files(paths: Iterable[str]) -> Iterable[pathlib.Path]:
    """Expand directories; accept .jsonl and .json, ignore everything else."""
    for raw in paths:
        p = pathlib.Path(raw).expanduser()
        if p.is_dir():
            for child in sorted(p.rglob("*")):
                if child.suffix in (".jsonl", ".json", ".ndjson") and child.is_file():
                    yield child
        elif p.is_file():
            yield p


def load_events(paths: Iterable[str]) -> List[Event]:
    """Parse every log under the given paths."""
    events: List[Event] = []
    for path in iter_files(paths):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            event = parse_line(line)
            if event is not None and event.usage.total > 0:
                if not event.session:
                    event.session = path.stem
                events.append(event)
    return events
