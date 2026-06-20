import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

HOST = "127.0.0.1"
PORT = 8765
BASE_URL = f"http://{HOST}:{PORT}"
RUNS_LATEST = Path(".pai") / "runs" / "latest"


def wait_for_server() -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            with urlopen(BASE_URL + "/health", timeout=0.5) as response:
                if response.status == 200:
                    return
        except URLError:
            time.sleep(0.1)

    raise SystemExit("server did not become ready")


def request_json(path: str, method: str = "GET") -> dict:
    request = Request(BASE_URL + path, method=method)
    with urlopen(request, timeout=2) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


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
    command = [
        "uv",
        "run",
        "pai",
        "run",
        sys.executable,
        "-m",
        "app.serve",
    ]
    print("$ " + " ".join(command), flush=True)

    server = subprocess.Popen(command)
    try:
        wait_for_server()

        print("GET /orders/100", flush=True)
        print(json.dumps(request_json("/orders/100"), sort_keys=True))

        print("POST /debug/thread-crash", flush=True)
        print(json.dumps(request_json("/debug/thread-crash", method="POST"), sort_keys=True))

        time.sleep(0.2)

        print("POST /debug/shutdown", flush=True)
        print(json.dumps(request_json("/debug/shutdown", method="POST"), sort_keys=True))
    finally:
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)

    print(f"server_exit_code={server.returncode}")
    if server.returncode != 0:
        raise SystemExit(server.returncode)

    summarize_latest_run()


if __name__ == "__main__":
    main()
