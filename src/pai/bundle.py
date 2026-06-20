"""Bundle builder — aggregates a PAI run dir into a single JSON-serialisable dict.

Reads ``events.jsonl`` from the run dir, partitions events by type, merges
``run_start`` and ``run_end`` into a single ``run`` section, and returns a
``BundleData`` typed dict that agents can consume as one structured artifact.
"""

import json
from pathlib import Path
from typing import NotRequired, TypedDict

__all__ = ["BundleData", "RunInfo", "build_bundle", "load_events"]

EVENTS_FILE = "events.jsonl"
SCHEMA_VERSION = 1


class RunInfo(TypedDict):
    command: list[str]
    cwd: str
    python_version: str
    exit_code: int
    duration_ms: int


class BundleData(TypedDict):
    schema_version: int
    run: RunInfo
    exceptions: list[dict]
    imports: list[dict]
    calls: list[dict]
    tests: list[dict]
    http: list[dict]
    sql: list[dict]
    aws: list[dict]
    ai: list[dict]
    unknown: NotRequired[list[dict]]


def load_events(run_dir: Path) -> list[dict]:
    """Read and parse every line of ``events.jsonl`` in ``run_dir``."""
    events_path = run_dir / EVENTS_FILE
    if not events_path.exists():
        return []
    result: list[dict] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            result.append(json.loads(stripped))
    return result


def build_bundle(run_dir: Path) -> BundleData:
    """Aggregate all events in ``run_dir`` into a structured bundle."""
    events = load_events(run_dir)

    run_start: dict = {}
    run_end: dict = {}
    exceptions: list[dict] = []
    imports: list[dict] = []
    calls: list[dict] = []
    tests: list[dict] = []
    http: list[dict] = []
    sql: list[dict] = []
    aws: list[dict] = []
    ai: list[dict] = []
    unknown: list[dict] = []

    for event in events:
        event_type = event.get("event", "")
        if event_type == "run_start":
            run_start = event
        elif event_type == "run_end":
            run_end = event
        elif event_type == "exception":
            exceptions.append(event)
        elif event_type == "import":
            imports.append(event)
        elif event_type == "call":
            calls.append(event)
        elif event_type == "test":
            tests.append(event)
        elif event_type == "http":
            http.append(event)
        elif event_type == "sql":
            sql.append(event)
        elif event_type == "aws":
            aws.append(event)
        elif event_type == "ai":
            ai.append(event)
        else:
            unknown.append(event)

    run: RunInfo = {
        "command": run_start.get("command", []),
        "cwd": run_start.get("cwd", ""),
        "python_version": run_start.get("python_version", ""),
        "exit_code": run_end.get("exit_code", -1),
        "duration_ms": run_end.get("duration_ms", 0),
    }

    bundle: BundleData = {
        "schema_version": SCHEMA_VERSION,
        "run": run,
        "exceptions": exceptions,
        "imports": imports,
        "calls": calls,
        "tests": tests,
        "http": http,
        "sql": sql,
        "aws": aws,
        "ai": ai,
    }

    if unknown:
        bundle["unknown"] = unknown

    return bundle
