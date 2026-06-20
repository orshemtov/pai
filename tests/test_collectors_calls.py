import json
import sys
import time
from pathlib import Path

from pai.collectors.calls import CallCollector
from pai.writer import EventWriter


def read_call_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "call":
            result.append(event)
    return result


def test_call_collector_emits_event_for_python_function(tmp_path: Path) -> None:
    with EventWriter(tmp_path) as writer:
        collector = CallCollector(writer=writer, original_profile=None)

        def target() -> int:
            return 42

        old = sys.getprofile()
        sys.setprofile(collector.profile_hook)
        target()
        sys.setprofile(old)

    events = read_call_events(tmp_path)

    assert len(events) >= 1
    event = events[0]
    assert event["schema_version"] == 1
    assert "target" in event["callee"]
    assert isinstance(event["duration_ms"], int)
    assert event["duration_ms"] >= 0
    assert "timestamp" in event


def test_call_collector_records_caller(tmp_path: Path) -> None:
    with EventWriter(tmp_path) as writer:
        collector = CallCollector(writer=writer, original_profile=None)

        def callee_fn() -> None:
            pass

        old = sys.getprofile()
        sys.setprofile(collector.profile_hook)
        callee_fn()
        sys.setprofile(old)

    events = read_call_events(tmp_path)

    assert len(events) >= 1
    assert isinstance(events[0]["caller"], str)
    assert len(events[0]["caller"]) > 0


def test_call_collector_duration_reflects_real_time(tmp_path: Path) -> None:
    with EventWriter(tmp_path) as writer:
        collector = CallCollector(writer=writer, original_profile=None)

        def slow_fn() -> None:
            time.sleep(0.05)

        old = sys.getprofile()
        sys.setprofile(collector.profile_hook)
        slow_fn()
        sys.setprofile(old)

    events = read_call_events(tmp_path)

    assert len(events) >= 1
    assert events[0]["duration_ms"] >= 40


def test_call_collector_records_file_and_line(tmp_path: Path) -> None:
    with EventWriter(tmp_path) as writer:
        collector = CallCollector(writer=writer, original_profile=None)

        def fn_with_location() -> None:
            pass

        old = sys.getprofile()
        sys.setprofile(collector.profile_hook)
        fn_with_location()
        sys.setprofile(old)

    events = read_call_events(tmp_path)

    assert len(events) >= 1
    assert events[0]["file"].endswith(".py")
    assert isinstance(events[0]["line"], int)
    assert events[0]["line"] > 0


def test_call_collector_chains_original_profile(tmp_path: Path) -> None:
    calls: list[str] = []

    def original(frame, event, arg) -> None:
        calls.append(event)

    with EventWriter(tmp_path) as writer:
        collector = CallCollector(writer=writer, original_profile=original)

        def fn() -> None:
            pass

        old = sys.getprofile()
        sys.setprofile(collector.profile_hook)
        fn()
        sys.setprofile(old)

    assert "call" in calls
    assert "return" in calls
