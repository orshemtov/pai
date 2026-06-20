"""Command-line entry point for PAI."""

import argparse
import json
import sys
from pathlib import Path

from pai import run as run_module
from pai import runner
from pai.bundle import build_bundle

__all__ = ["main"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pai", description="Python AI runtime tracing.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    run_parser = subcommands.add_parser("run", help="Run a command with PAI tracing.")
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        if not args.cmd:
            parser.error("`run` requires a command, e.g. `pai run python app.py`")
        return runner.run(args.cmd)

    if args.command == "bundle":
        run_dir = Path(args.run) if args.run else run_module.latest_pointer()

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

    parser.error(f"unknown command: {args.command}")
    return 2
