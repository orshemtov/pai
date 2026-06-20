import builtins
import json
from pathlib import Path

from pai.collectors.imports import ImportCollector, resolve_module_name
from pai.writer import EventWriter


def read_import_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "import":
            result.append(event)
    return result


def test_resolve_absolute_import() -> None:
    assert resolve_module_name("json", package="", level=0) == "json"


def test_resolve_relative_import_one_level() -> None:
    assert resolve_module_name("models", package="app", level=1) == "app.models"


def test_resolve_relative_import_two_levels() -> None:
    assert resolve_module_name("models", package="app.views", level=2) == "app.models"


def test_resolve_relative_import_empty_name() -> None:
    assert resolve_module_name("", package="app", level=1) == "app"


def test_import_collector_records_absolute_import(tmp_path: Path) -> None:
    with EventWriter(tmp_path) as writer:
        collector = ImportCollector(writer=writer, original_import=builtins.__import__)

        fake_globals: dict = {"__name__": "app.orders", "__package__": "app"}
        collector.patched_import("json", globals=fake_globals)

    events = read_import_events(tmp_path)

    assert len(events) == 1
    assert events[0]["module"] == "app.orders"
    assert events[0]["imported"] == "json"
    assert events[0]["schema_version"] == 1
    assert "timestamp" in events[0]


def test_import_collector_deduplicates_same_edge(tmp_path: Path) -> None:
    with EventWriter(tmp_path) as writer:
        collector = ImportCollector(writer=writer, original_import=builtins.__import__)

        fake_globals: dict = {"__name__": "app.orders", "__package__": "app"}
        collector.patched_import("json", globals=fake_globals)
        collector.patched_import("json", globals=fake_globals)

    events = read_import_events(tmp_path)

    assert len(events) == 1


def test_import_collector_records_different_callers(tmp_path: Path) -> None:
    with EventWriter(tmp_path) as writer:
        collector = ImportCollector(writer=writer, original_import=builtins.__import__)

        globals_a: dict = {"__name__": "app.orders", "__package__": "app"}
        globals_b: dict = {"__name__": "app.views", "__package__": "app"}
        collector.patched_import("json", globals=globals_a)
        collector.patched_import("json", globals=globals_b)

    events = read_import_events(tmp_path)

    assert len(events) == 2


def test_import_collector_handles_none_globals(tmp_path: Path) -> None:
    with EventWriter(tmp_path) as writer:
        collector = ImportCollector(writer=writer, original_import=builtins.__import__)
        collector.patched_import("json", globals=None)

    events = read_import_events(tmp_path)

    assert len(events) == 1
    assert events[0]["module"] == "__unknown__"
