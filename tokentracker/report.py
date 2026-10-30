"""Rendering: a static report, and a live dashboard for `watch`."""

from __future__ import annotations

import json
import shutil
from typing import List, Optional

from .attribute import UNATTRIBUTED, Analysis

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
YELLOW = "\033[33m"


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _fmt_cost(value: Optional[float]) -> str:
    if value is None:
        return "-"
    if value < 0.01:
        return f"${value:.4f}"
    return f"${value:.2f}"


def _bar(percent: float, width: int = 24) -> str:
    filled = int(round(percent / 100.0 * width))
    return "#" * filled + "." * (width - filled)


def _label(name: str, width: int) -> str:
    label = name if len(name) <= width else "..." + name[-(width - 3):]
    return label.ljust(width)


def render_json(analysis: Analysis) -> str:
    payload = {
        "events": analysis.events,
        "tokens": {
            "total": analysis.total.total,
            "input": analysis.total.input,
            "output": analysis.total.output,
            "cache_read": analysis.total.cache_read,
            "cache_write": analysis.total.cache_write,
        },
        "cost_usd": analysis.cost_usd,
        "unpriced_models": analysis.unpriced_models,
        "sessions": {
            name: {"tokens": usage.total, "cost_usd": analysis.session_cost.get(name)}
            for name, usage in sorted(analysis.sessions.items(), key=lambda kv: -kv[1].total)
        },
        "targets": [
            {
                "name": name,
                "tokens": _usage.total,
                "share_pct": round(analysis.share(name), 1),
                "cost_usd": analysis.bucket_cost.get(name),
            }
            for name, _usage in analysis.top(len(analysis.buckets))
        ],
    }
    return json.dumps(payload, indent=2)


def render_text(analysis: Analysis, top: int = 5, label_width: Optional[int] = None) -> str:
    """The report a human reads. Percentages always sum to the total spend."""
    if not analysis.events:
        return "tokentracker: no model calls found in the given paths.\n"

    width = label_width or 40
    lines: List[str] = []
    lines.append(f"tokentracker: {analysis.events} model calls, {_fmt_tokens(analysis.total.total)} tokens")
    if analysis.cost_usd is None:
        lines.append("cost: unavailable (no price for these models; pass --prices file.json)")
    else:
        lines.append(f"cost: {_fmt_cost(analysis.cost_usd)} (estimate, prices as of the loaded table)")
    if analysis.unpriced_models:
        lines.append(f"unpriced models: {', '.join(analysis.unpriced_models)}")

    lines.append("")
    lines.append(BOLD + "Where the context went" + RESET)
    for name, usage in analysis.top(top):
        pct = analysis.share(name)
        tag = ""
        if pct >= 40:
            tag = RED + "  <- the expensive one" + RESET
        elif pct >= 20:
            tag = YELLOW + "  <- worth a look" + RESET
        lines.append(
            f"  {_label(name, width)} {_fmt_tokens(usage.total):>8}  {pct:5.1f}%  "
            f"[{_bar(pct)}] {_fmt_cost(analysis.bucket_cost.get(name))}{tag}"
        )
    hidden = len(analysis.buckets) - min(top, len(analysis.buckets))
    if hidden > 0:
        lines.append(f"  {DIM}... {hidden} more target(s); use --top to see them{RESET}")

    lines.append("")
    lines.append(BOLD + "Sessions" + RESET)
    for name, usage in sorted(analysis.sessions.items(), key=lambda kv: -kv[1].total):
        share = 100.0 * usage.total / analysis.total.total if analysis.total.total else 0.0
        lines.append(
            f"  {_label(name or '(default)', width)} {_fmt_tokens(usage.total):>8}  {share:5.1f}%  "
            f"{_fmt_cost(analysis.session_cost.get(name))}"
        )

    if UNATTRIBUTED in analysis.buckets:
        lines.append("")
        lines.append(
            f"{DIM}Calls with no file or skill reference land in {UNATTRIBUTED}; "
            f"a call that touches three files splits its tokens evenly across them.{RESET}"
        )
    return "\n".join(lines) + "\n"


def render_dashboard(analysis: Analysis, top: int = 3) -> str:
    """Compact, screen-clearable frame for `tokentracker watch`."""
    cols = shutil.get_terminal_size((100, 30)).columns
    if not analysis.events:
        return "\033[2J\033[3;1Htokentracker: waiting for model calls...\n"
    lines = ["\033[2J\033[3;1H" + BOLD + "tokentracker" + RESET + f"  {analysis.events} calls  "
             f"{_fmt_tokens(analysis.total.total)} tokens  {_fmt_cost(analysis.cost_usd)}"]
    for name, usage in analysis.top(top):
        pct = analysis.share(name)
        lines.append(f"  {_label(name, cols - 20)} {_fmt_tokens(usage.total):>7} {pct:5.1f}%")
    lines.append(DIM + "  ctrl-c to stop" + RESET)
    return "\n".join(lines) + "\n"
