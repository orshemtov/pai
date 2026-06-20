"""Bundle builder — aggregates a PAI run dir into a single JSON-serialisable dict.

Reads ``events.jsonl`` from the run dir, partitions events by type, merges
``run_start`` and ``run_end`` into a single ``run`` section, and returns a
``BundleData`` typed dict that agents can consume as one structured artifact.
"""

import json
from pathlib import Path
from typing import NotRequired, TypedDict

from pai.event_names import EventName, is_side_effect_event
from pai.event_records import EventRecord

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
    effects: dict[str, list[dict]]
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
    effects: dict[str, list[dict]] = {}
    unknown: list[dict] = []

    for event in events:
        event_type = EventRecord(event).name
        match event_type:
            case EventName.RUN_START:
                run_start = event
            case EventName.RUN_END:
                run_end = event
            case EventName.EXCEPTION:
                exceptions.append(event)
            case EventName.IMPORT:
                imports.append(event)
            case EventName.CALL:
                calls.append(event)
            case EventName.TEST:
                tests.append(event)
            case EventName() as package if is_side_effect_event(package):
                events_for_package = effects.setdefault(package.value, [])
                events_for_package.append(event)
            case _:
                unknown.append(event)

    command: list[str] = []
    cwd = ""
    python_version = ""
    exit_code = -1
    duration_ms = 0

    if run_start:
        command_value = run_start["command"]
        if isinstance(command_value, list):
            for part in command_value:
                command.append(str(part))
        cwd = str(run_start["cwd"])
        python_version = str(run_start["python_version"])

    if run_end:
        exit_code = int(run_end["exit_code"])
        duration_ms = int(run_end["duration_ms"])

    run: RunInfo = {
        "command": command,
        "cwd": cwd,
        "python_version": python_version,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
    }

    bundle: BundleData = {
        "schema_version": SCHEMA_VERSION,
        "run": run,
        "exceptions": exceptions,
        "imports": imports,
        "calls": calls,
        "tests": tests,
        "effects": effects,
    }

    if unknown:
        bundle["unknown"] = unknown

    return bundle
