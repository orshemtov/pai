"""Command-line entry point for PAI."""

import argparse

from pai import runner

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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        if not args.cmd:
            parser.error("`run` requires a command, e.g. `pai run python app.py`")
        return runner.run(args.cmd)

    parser.error(f"unknown command: {args.command}")
    return 2
