"""Agent-facing query helpers for compact run inspection."""

from collections import Counter
from pathlib import Path
from typing import TypedDict

from pai.event_names import EventName, is_side_effect_event
from pai.event_records import (
    EventRecord,
    event_id_for,
    event_type_text,
    optional_text,
    required_text,
)
from pai.run_events import load_run_events

__all__ = [
    "EffectsQuery",
    "FailuresQuery",
    "RepairContextQuery",
    "StatusQuery",
    "SymbolQuery",
    "TestsQuery",
    "TimelineQuery",
    "build_effects",
    "build_failures",
    "build_repair_context",
    "build_status",
    "build_symbol",
    "build_tests",
    "build_timeline",
]

SCHEMA_VERSION = 1


class TopFailure(TypedDict):
    event_id: str
    kind: str
    message: str
    test_id: str


class StatusQuery(TypedDict):
    schema_version: int
    run_id: str
    command: list[str]
    cwd: str
    exit_code: int
    duration_ms: int
    event_counts: dict[str, int]
    failed_tests: int
    exceptions: int
    top_failure: dict


class FailuresQuery(TypedDict):
    schema_version: int
    run_id: str
    failed_tests: list[dict]
    exceptions: list[dict]


class TestsQuery(TypedDict):
    schema_version: int
    run_id: str
    summary: dict[str, int]
    tests: list[dict]


class EffectsQuery(TypedDict):
    schema_version: int
    run_id: str
    summary: dict[str, int]
    packages: dict[str, list[dict]]


class TimelineQuery(TypedDict):
    schema_version: int
    run_id: str
    limit: int
    events: list[dict]


class SymbolQuery(TypedDict):
    schema_version: int
    run_id: str
    name: str
    exceptions: list[dict]
    calls: list[dict]
    imports: list[dict]


class RepairContextQuery(TypedDict):
    schema_version: int
    run_id: str
    event: dict
    symbol: str
    related_calls: list[dict]
    related_tests: list[dict]
    recent_effects: list[dict]


def run_id_for(run_dir: Path) -> str:
    return load_run_events(run_dir).run_id


def count_events(events: list[dict]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for event in events:
        counter[event_type_text(event)] += 1

    result: dict[str, int] = {}
    for name in sorted(counter):
        result[name] = counter[name]
    return result


def top_failure_from(events: list[dict]) -> dict:
    for event in events:
        match EventRecord(event).name:
            case EventName.TEST if required_text(event, "outcome") == "failed":
                return {
                    "event_id": event_id_for(event),
                    "kind": "test",
                    "test_id": required_text(event, "test_id"),
                    "message": required_text(event, "message"),
                }
            case _:
                continue

    for event in events:
        match EventRecord(event).name:
            case EventName.EXCEPTION:
                return {
                    "event_id": event_id_for(event),
                    "kind": "exception",
                    "symbol": required_text(event, "symbol"),
                    "exception_type": required_text(event, "exception_type"),
                    "message": required_text(event, "message"),
                }
            case _:
                continue

    return {}


def build_status(run_dir: Path) -> StatusQuery:
    run_events = load_run_events(run_dir)
    run_start = run_events.run_start
    run_end = run_events.run_end

    command: list[str] = []
    cwd = ""
    exit_code = -1
    duration_ms = 0

    if run_start:
        command_value = run_start["command"]
        if isinstance(command_value, list):
            for part in command_value:
                command.append(str(part))
        cwd = required_text(run_start, "cwd")

    if run_end:
        exit_code = int(run_end["exit_code"])
        duration_ms = int(run_end["duration_ms"])

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_events.run_id,
        "command": command,
        "cwd": cwd,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "event_counts": count_events(run_events.events),
        "failed_tests": len(run_events.failed_tests),
        "exceptions": len(run_events.exceptions),
        "top_failure": top_failure_from(run_events.events),
    }


def build_failures(run_dir: Path) -> FailuresQuery:
    run_events = load_run_events(run_dir)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_events.run_id,
        "failed_tests": run_events.failed_tests,
        "exceptions": run_events.exceptions,
    }


def build_tests(run_dir: Path) -> TestsQuery:
    run_events = load_run_events(run_dir)
    summary: dict[str, int] = {}

    for event in run_events.tests:
        outcome = required_text(event, "outcome")
        current = 0
        if outcome in summary:
            current = summary[outcome]
        summary[outcome] = current + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_events.run_id,
        "summary": summary,
        "tests": run_events.tests,
    }


def build_effects(run_dir: Path) -> EffectsQuery:
    run_events = load_run_events(run_dir)
    packages = run_events.effects_by_package
    summary: dict[str, int] = {}

    for package in sorted(packages):
        summary[package] = len(packages[package])

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_events.run_id,
        "summary": summary,
        "packages": packages,
    }


def build_timeline(run_dir: Path, limit: int) -> TimelineQuery:
    run_events = load_run_events(run_dir)
    selected: list[dict] = []

    for event in run_events.events:
        if len(selected) >= limit:
            break
        selected.append(event)

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_events.run_id,
        "limit": limit,
        "events": selected,
    }


def event_matches_symbol(event: dict, name: str) -> bool:
    event_symbol = optional_text(event, "symbol")
    if event_symbol == name:
        return True

    caller = optional_text(event, "caller")
    if caller == name:
        return True

    callee = optional_text(event, "callee")
    if callee == name:
        return True

    module = optional_text(event, "module")
    if module == name:
        return True

    imported = optional_text(event, "imported")
    return imported == name


def build_symbol(run_dir: Path, name: str) -> SymbolQuery:
    run_events = load_run_events(run_dir)
    exceptions: list[dict] = []
    calls: list[dict] = []
    imports: list[dict] = []

    for event in run_events.events:
        if not event_matches_symbol(event, name):
            continue

        match EventRecord(event).name:
            case EventName.EXCEPTION:
                exceptions.append(event)
            case EventName.CALL:
                calls.append(event)
            case EventName.IMPORT:
                imports.append(event)

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_events.run_id,
        "name": name,
        "exceptions": exceptions,
        "calls": calls,
        "imports": imports,
    }


def symbol_for_event(event: dict) -> str:
    symbol = optional_text(event, "symbol")
    if symbol:
        return symbol

    callee = optional_text(event, "callee")
    if callee:
        return callee

    return optional_text(event, "test_id")


def related_calls_for(events: list[dict], symbol: str) -> list[dict]:
    result: list[dict] = []
    if not symbol:
        return result

    for event in events:
        match EventRecord(event).name:
            case EventName.CALL if event_matches_symbol(event, symbol):
                result.append(event)
            case _:
                continue
    return result


def recent_effects_from(events: list[dict]) -> list[dict]:
    result: list[dict] = []
    for event in events:
        match EventRecord(event).name:
            case EventName() as event_name if is_side_effect_event(event_name):
                result.append(event)
            case _:
                continue
    return result


def build_repair_context(run_dir: Path, event_id: str) -> RepairContextQuery:
    run_events = load_run_events(run_dir)
    event = run_events.event_by_id(event_id)
    symbol = symbol_for_event(event)

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_events.run_id,
        "event": event,
        "symbol": symbol,
        "related_calls": related_calls_for(run_events.events, symbol),
        "related_tests": run_events.failed_tests,
        "recent_effects": recent_effects_from(run_events.events),
    }
