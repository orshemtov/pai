import json
import sys
from pathlib import Path
from typing import cast

from pai import run, runner

FIXTURE = """\
def parse_user(payload):
    return payload["user_id"]


parse_user({"name": "John"})
"""

IMPORT_FIXTURE = """\
import json
import os

data = json.dumps({"key": str(os.getpid())})
print(data)
"""

CALL_FIXTURE = """\
def add(a, b):
    return a + b


def multiply(a, b):
    total = 0
    for _ in range(b):
        total = add(total, a)
    return total


result = multiply(3, 4)
print(result)
"""


def read_events(events_path: Path) -> list[dict]:
    events: list[dict] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        events.append(json.loads(line))
    return events


def events_of_type(events: list[dict], event_type: str) -> list[dict]:
    result: list[dict] = []
    for event in events:
        if event["event"] == event_type:
            result.append(event)
    return result


def test_pai_run_captures_structured_exception(tmp_path: Path) -> None:
    script = tmp_path / "main.py"
    script.write_text(FIXTURE, encoding="utf-8")

    exit_code = runner.run([sys.executable, str(script)], base=tmp_path)

    assert exit_code != 0

    events_path = run.latest_pointer(base=tmp_path) / "events.jsonl"
    events = read_events(events_path)

    exception_events = events_of_type(events, "exception")

    assert len(exception_events) == 1

    exc = exception_events[0]
    assert exc["schema_version"] == 1
    assert exc["exception_type"] == "KeyError"
    assert exc["message"] == "'user_id'"

    symbol = exc["symbol"]
    assert isinstance(symbol, str) and symbol.endswith(".parse_user")

    assert exc["locals_schema"] == {"payload": {"type": "dict", "keys": ["name"]}}

    assert "timestamp" in exc


def test_pai_run_emits_run_start_event(tmp_path: Path) -> None:
    script = tmp_path / "main.py"
    script.write_text(FIXTURE, encoding="utf-8")

    runner.run([sys.executable, str(script)], base=tmp_path)

    events_path = run.latest_pointer(base=tmp_path) / "events.jsonl"
    events = read_events(events_path)

    start_events = events_of_type(events, "run_start")

    assert len(start_events) == 1

    start = start_events[0]
    assert start["schema_version"] == 1

    command = cast(list, start["command"])
    assert str(script) in command

    assert "timestamp" in start


def test_pai_run_emits_run_end_event(tmp_path: Path) -> None:
    script = tmp_path / "main.py"
    script.write_text(FIXTURE, encoding="utf-8")

    exit_code = runner.run([sys.executable, str(script)], base=tmp_path)

    events_path = run.latest_pointer(base=tmp_path) / "events.jsonl"
    events = read_events(events_path)

    end_events = events_of_type(events, "run_end")

    assert len(end_events) == 1

    end = end_events[0]
    assert end["schema_version"] == 1
    assert end["exit_code"] == exit_code

    duration = end["duration_ms"]
    assert isinstance(duration, int)
    assert duration >= 0

    assert "timestamp" in end


def test_pai_run_captures_import_events(tmp_path: Path) -> None:
    script = tmp_path / "script.py"
    script.write_text(IMPORT_FIXTURE, encoding="utf-8")

    exit_code = runner.run([sys.executable, str(script)], base=tmp_path)

    assert exit_code == 0

    events_path = run.latest_pointer(base=tmp_path) / "events.jsonl"
    events = read_events(events_path)

    import_events = events_of_type(events, "import")

    imported_names: list = []
    for event in import_events:
        imported_names.append(event["imported"])

    assert "json" in imported_names
    assert "os" in imported_names


def test_pai_run_captures_call_events(tmp_path: Path) -> None:
    script = tmp_path / "script.py"
    script.write_text(CALL_FIXTURE, encoding="utf-8")

    exit_code = runner.run([sys.executable, str(script)], base=tmp_path)

    assert exit_code == 0

    events_path = run.latest_pointer(base=tmp_path) / "events.jsonl"
    events = read_events(events_path)

    call_events = events_of_type(events, "call")

    assert len(call_events) >= 1

    callees: list = []
    for event in call_events:
        callees.append(event["callee"])

    assert any("add" in str(c) for c in callees)
    assert any("multiply" in str(c) for c in callees)


def test_events_are_ordered_start_then_exception_then_end(tmp_path: Path) -> None:
    script = tmp_path / "main.py"
    script.write_text(FIXTURE, encoding="utf-8")

    runner.run([sys.executable, str(script)], base=tmp_path)

    events_path = run.latest_pointer(base=tmp_path) / "events.jsonl"
    events = read_events(events_path)

    event_types: list = []
    for event in events:
        event_types.append(event["event"])

    assert event_types[0] == "run_start"
    assert event_types[-1] == "run_end"
    assert "exception" in event_types
