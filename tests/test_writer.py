import json
import threading
from pathlib import Path

from pai.events import ExceptionEvent
from pai.writer import EventWriter


def make_event(message: str) -> ExceptionEvent:
    return ExceptionEvent(
        symbol="main.parse_user",
        file="main.py",
        line=2,
        exception_type="KeyError",
        message=message,
        locals_schema={"payload": {"type": "dict", "keys": ["name"]}},
    )


def without_timestamp(data: dict) -> dict:
    result: dict = {}
    for key, value in data.items():
        if key != "timestamp" and key != "event_id" and key != "run_id":
            result[key] = value
    return result


def test_write_appends_jsonl_line(tmp_path: Path) -> None:
    event = make_event("'user_id'")

    with EventWriter(tmp_path) as writer:
        writer.write(event)

    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1

    parsed = json.loads(lines[0])

    assert "timestamp" in parsed
    assert parsed["run_id"] == tmp_path.name
    assert parsed["event_id"] == "evt_000001"
    assert without_timestamp(parsed) == event.to_dict()


def test_write_fans_out_to_per_type_file(tmp_path: Path) -> None:
    event = make_event("'user_id'")

    with EventWriter(tmp_path) as writer:
        writer.write(event)

    lines = (tmp_path / "exceptions.json").read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1

    parsed = json.loads(lines[0])

    assert "timestamp" in parsed
    assert parsed["run_id"] == tmp_path.name
    assert parsed["event_id"] == "evt_000001"
    assert without_timestamp(parsed) == event.to_dict()


def test_write_is_thread_safe(tmp_path: Path) -> None:
    writer = EventWriter(tmp_path)
    threads: list[threading.Thread] = []
    for index in range(50):
        thread = threading.Thread(target=writer.write, args=(make_event(str(index)),))
        threads.append(thread)

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    writer.close()

    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()

    assert len(lines) == 50
    for line in lines:
        json.loads(line)


def test_write_assigns_stable_sequential_event_ids(tmp_path: Path) -> None:
    with EventWriter(tmp_path) as writer:
        writer.write(make_event("first"))
        writer.write(make_event("second"))
        writer.write(make_event("third"))

    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()

    event_ids: list[str] = []
    for line in lines:
        event_ids.append(str(json.loads(line)["event_id"]))

    assert event_ids == ["evt_000001", "evt_000002", "evt_000003"]
