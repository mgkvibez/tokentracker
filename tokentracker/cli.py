"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
import time
import pathlib

from . import __version__
from .adapters import load_events
from .attribute import analyse
from .pricing import AS_OF, load_prices
from .report import render_dashboard, render_json, render_text


def _analyse(args: argparse.Namespace):
    events = load_events(args.paths)
    return analyse(events, getattr(args, "prices", None))


def cmd_report(args: argparse.Namespace) -> int:
    analysis = _analyse(args)
    print(render_json(analysis) if args.json else render_text(analysis, top=args.top), end="")
    return 0 if analysis.events else 1


def cmd_watch(args: argparse.Namespace) -> int:
    print("\033[?25l", end="")          # hide cursor
    try:
        while True:
            analysis = _analyse(args)
            sys.stdout.write(render_dashboard(analysis))
            sys.stdout.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        print("\033[?25h", end="")      # restore cursor


def cmd_proxy(args: argparse.Namespace) -> int:
    from .proxy import serve
    serve(args.port, args.upstream, pathlib.Path(args.log).expanduser(), args.verbose)
    return 0


def cmd_prices(args: argparse.Namespace) -> int:
    prices = load_prices(args.prices)
    print(f"prices as of {AS_OF} (defaults are editable; verify against your provider)")
    print(f'{"model":26}{"input $/M":>12}{"output $/M":>12}')
    for model in sorted(prices):
        rates = prices[model]
        print(f'{model:26}{rates["input"]:>12.2f}{rates["output"]:>12.2f}')
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tokentracker",
        description="See where your agent sessions spend tokens: per session, per file, per skill.",
    )
    parser.add_argument("--version", action="version", version=f"tokentracker {__version__}")
    subs = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("paths", nargs="+", help="harness logs: files or directories")
    common.add_argument("--prices", help="JSON price table to use instead of the built-in defaults")

    p_report = subs.add_parser("report", parents=[common], help="one-shot report")
    p_report.add_argument("--json", action="store_true", help="machine-readable output")
    p_report.add_argument("--top", type=int, default=5, help="how many context eaters to show")
    p_report.set_defaults(func=cmd_report)

    p_watch = subs.add_parser("watch", parents=[common], help="live dashboard, redrawn every interval")
    p_watch.add_argument("--interval", type=float, default=1.0, help="seconds between redraws")
    p_watch.add_argument("--top", type=int, default=3)
    p_watch.set_defaults(func=cmd_watch)

    p_proxy = subs.add_parser("proxy", help="record usage by proxying API calls")
    p_proxy.add_argument("--port", type=int, default=8787)
    p_proxy.add_argument("--upstream", default="https://api.anthropic.com")
    p_proxy.add_argument("--log", default="~/.tokentracker/proxy.jsonl")
    p_proxy.add_argument("--verbose", action="store_true")
    p_proxy.set_defaults(func=cmd_proxy)

    p_prices = subs.add_parser("prices", help="show the price table in use")
    p_prices.add_argument("--prices", help="JSON price table to inspect")
    p_prices.set_defaults(func=cmd_prices)
    return parser


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
