"""Command-line entry point for PAI."""

import argparse
import json
import sys
from enum import StrEnum
from pathlib import Path

from pai import query, run, runner
from pai.bundle import build_bundle

__all__ = ["main"]


class Command(StrEnum):
    BUNDLE = "bundle"
    QUERY = "query"
    RUN = "run"


class QueryCommand(StrEnum):
    EFFECTS = "effects"
    FAILURES = "failures"
    REPAIR_CONTEXT = "repair-context"
    STATUS = "status"
    SYMBOL = "symbol"
    TESTS = "tests"
    TIMELINE = "timeline"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pai", description="Python AI runtime tracing.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    run_parser = subcommands.add_parser("run", help="Run a command with PAI tracing.")
    run_parser.add_argument(
        "--summary-json",
        action="store_true",
        help="Print compact run status JSON after the target command exits.",
    )
    run_parser.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="The command to run, e.g. `pai run python app.py`.",
    )

    bundle_parser = subcommands.add_parser(
        "bundle",
        help="Aggregate a run dir into a single JSON bundle for agents.",
    )
    bundle_parser.add_argument(
        "--run",
        metavar="PATH",
        help="Path to run dir (default: .pai/runs/latest).",
    )
    bundle_parser.add_argument(
        "--out",
        metavar="FILE",
        help="Write bundle to FILE instead of stdout.",
    )

    query_parser = subcommands.add_parser(
        "query",
        help="Inspect a run with compact agent-facing JSON queries.",
    )
    query_subcommands = query_parser.add_subparsers(dest="query_command", required=True)

    query_names = [
        QueryCommand.STATUS,
        QueryCommand.FAILURES,
        QueryCommand.TESTS,
        QueryCommand.EFFECTS,
    ]
    for name in query_names:
        item_parser = query_subcommands.add_parser(name, help=f"Run `{name}` query.")
        item_parser.add_argument(
            "--run",
            metavar="PATH",
            help="Path to run dir (default: .pai/runs/latest).",
        )

    timeline_parser = query_subcommands.add_parser(
        "timeline",
        help="Return a compact ordered event slice.",
    )
    timeline_parser.add_argument(
        "--run",
        metavar="PATH",
        help="Path to run dir (default: .pai/runs/latest).",
    )
    timeline_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of events to include.",
    )

    symbol_parser = query_subcommands.add_parser(
        "symbol",
        help="Return events related to one symbol.",
    )
    symbol_parser.add_argument(
        "--run",
        metavar="PATH",
        help="Path to run dir (default: .pai/runs/latest).",
    )
    symbol_parser.add_argument(
        "--name",
        required=True,
        help="Symbol name to inspect.",
    )

    repair_parser = query_subcommands.add_parser(
        "repair-context",
        help="Return a compact repair context for one event.",
    )
    repair_parser.add_argument(
        "--run",
        metavar="PATH",
        help="Path to run dir (default: .pai/runs/latest).",
    )
    repair_parser.add_argument(
        "--event",
        required=True,
        help="Event id to inspect, e.g. evt_000003.",
    )

    return parser


def resolve_run_dir(path: str | None) -> Path:
    if path:
        return Path(path)
    return run.latest_pointer()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    match args.command:
        case Command.RUN:
            if not args.cmd:
                parser.error("`run` requires a command, e.g. `pai run python app.py`")
            exit_code = runner.run(args.cmd)
            if args.summary_json:
                run_dir = run.latest_pointer()
                summary = query.build_status(run_dir)
                print(json.dumps(summary, indent=2))
            return exit_code

        case Command.BUNDLE:
            run_dir = resolve_run_dir(args.run)

            if not run_dir.exists():
                print(f"error: run dir not found: {run_dir}", file=sys.stderr)
                return 1

            bundle = build_bundle(run_dir)
            output = json.dumps(bundle, indent=2)

            if args.out:
                Path(args.out).write_text(output + "\n", encoding="utf-8")
            else:
                print(output)

            return 0

        case Command.QUERY:
            run_dir = resolve_run_dir(args.run)

            if not run_dir.exists():
                print(f"error: run dir not found: {run_dir}", file=sys.stderr)
                return 1

            match args.query_command:
                case QueryCommand.STATUS:
                    result = query.build_status(run_dir)
                case QueryCommand.FAILURES:
                    result = query.build_failures(run_dir)
                case QueryCommand.TESTS:
                    result = query.build_tests(run_dir)
                case QueryCommand.EFFECTS:
                    result = query.build_effects(run_dir)
                case QueryCommand.TIMELINE:
                    result = query.build_timeline(run_dir, args.limit)
                case QueryCommand.SYMBOL:
                    result = query.build_symbol(run_dir, args.name)
                case QueryCommand.REPAIR_CONTEXT:
                    result = query.build_repair_context(run_dir, args.event)
                case _:
                    parser.error(f"unknown query command: {args.query_command}")
                    return 2

            output = json.dumps(result, indent=2)
            print(output)
            return 0

        case _:
            parser.error(f"unknown command: {args.command}")
            return 2
