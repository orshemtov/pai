import json
import subprocess
import sys
from pathlib import Path

RUNS_LATEST = Path(".pai") / "runs" / "latest"


def run_command(args: list[str], expect_success: bool) -> None:
    print("$ " + " ".join(args), flush=True)
    completed = subprocess.run(args, check=False)
    print(f"exit_code={completed.returncode}")

    if expect_success and completed.returncode != 0:
        raise SystemExit(completed.returncode)

    if not expect_success and completed.returncode == 0:
        raise SystemExit("expected command to fail, but it succeeded")


def load_latest_events() -> list[dict]:
    path = RUNS_LATEST / "events.jsonl"
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        events.append(json.loads(line))
    return events


def summarize_latest_run() -> None:
    events = load_latest_events()

    counts: dict[str, int] = {}
    for event in events:
        name = str(event["event"])
        current = counts.get(name, 0)
        counts[name] = current + 1

    print("latest run events:")
    for name, count in sorted(counts.items()):
        print(f"  {name}: {count}")

    for event in events:
        if event["event"] == "exception":
            print("exception:")
            print(f"  type: {event['exception_type']}")
            print(f"  symbol: {event['symbol']}")
            print(f"  locals_schema: {json.dumps(event['locals_schema'], sort_keys=True)}")


def main() -> None:
    run_command(
        ["uv", "run", "pai", "run", sys.executable, "scripts/successful_order.py"],
        expect_success=True,
    )
    summarize_latest_run()

    run_command(
        ["uv", "run", "pai", "run", sys.executable, "scripts/failing_order.py"],
        expect_success=False,
    )
    summarize_latest_run()


if __name__ == "__main__":
    main()
