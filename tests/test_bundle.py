"""Tests for pai bundle — run-dir aggregation into agent-consumable JSON."""

import json
import sys
from pathlib import Path

import pai.run
from pai import runner
from pai.bundle import build_bundle, load_events

SCRIPT_RAISES = """\
def parse(payload):
    return payload["user_id"]

parse({"name": "John"})
"""

SCRIPT_CLEAN = """\
import os
print(os.getpid())
"""


def write_events(run_dir: Path, events: list[dict]) -> None:
    path = run_dir / "events.jsonl"
    lines = []
    for event in events:
        lines.append(json.dumps(event))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_load_events_empty_dir(tmp_path: Path) -> None:
    assert load_events(tmp_path) == []


def test_load_events_reads_jsonl(tmp_path: Path) -> None:
    write_events(tmp_path, [{"event": "run_start"}, {"event": "run_end"}])
    events = load_events(tmp_path)
    assert len(events) == 2
    assert events[0]["event"] == "run_start"


def test_build_bundle_empty(tmp_path: Path) -> None:
    bundle = build_bundle(tmp_path)
    assert bundle["schema_version"] == 1
    assert bundle["exceptions"] == []
    assert bundle["imports"] == []
    assert bundle["calls"] == []
    assert bundle["tests"] == []
    assert bundle["effects"] == {}


def test_build_bundle_merges_run_start_and_end(tmp_path: Path) -> None:
    write_events(
        tmp_path,
        [
            {
                "event": "run_start",
                "command": ["python", "app.py"],
                "cwd": "/app",
                "python_version": "3.13",
            },
            {"event": "run_end", "exit_code": 0, "duration_ms": 42},
        ],
    )
    bundle = build_bundle(tmp_path)
    assert bundle["run"]["command"] == ["python", "app.py"]
    assert bundle["run"]["cwd"] == "/app"
    assert bundle["run"]["exit_code"] == 0
    assert bundle["run"]["duration_ms"] == 42


def test_build_bundle_groups_effects_by_concrete_package(tmp_path: Path) -> None:
    write_events(
        tmp_path,
        [
            {"event": "exception", "exception_type": "KeyError"},
            {"event": "import", "module": "app", "imported": "json"},
            {"event": "import", "module": "app", "imported": "os"},
            {"event": "call", "callee": "app.main", "caller": "__main__", "duration_ms": 1},
            {"event": "requests", "method": "GET", "url": "https://x.com", "status_code": 200},
            {"event": "sqlalchemy", "operation": "SELECT", "query": "SELECT 1", "duration_ms": 2},
            {"event": "boto3", "service": "s3", "operation": "GetObject", "duration_ms": 5},
            {"event": "openai", "model": "gpt-4o", "input_tokens": 10},
        ],
    )
    bundle = build_bundle(tmp_path)
    assert len(bundle["exceptions"]) == 1
    assert len(bundle["imports"]) == 2
    assert len(bundle["calls"]) == 1
    assert len(bundle["effects"]["requests"]) == 1
    assert len(bundle["effects"]["sqlalchemy"]) == 1
    assert len(bundle["effects"]["boto3"]) == 1
    assert len(bundle["effects"]["openai"]) == 1


def test_build_bundle_is_json_serialisable(tmp_path: Path) -> None:
    write_events(
        tmp_path,
        [
            {"event": "run_start", "command": ["python"], "cwd": "/", "python_version": "3.13"},
            {"event": "exception", "exception_type": "ValueError", "message": "oops"},
        ],
    )
    bundle = build_bundle(tmp_path)
    serialised = json.dumps(bundle)
    parsed = json.loads(serialised)
    assert parsed["schema_version"] == 1


def test_bundle_integration_exception_run(tmp_path: Path) -> None:
    script = tmp_path / "app.py"
    script.write_text(SCRIPT_RAISES, encoding="utf-8")

    runner.run([sys.executable, str(script)], base=tmp_path)

    run_dir = pai.run.latest_pointer(base=tmp_path)
    bundle = build_bundle(run_dir)

    assert bundle["run"]["exit_code"] != 0
    assert len(bundle["exceptions"]) == 1
    assert bundle["exceptions"][0]["exception_type"] == "KeyError"
    assert len(bundle["imports"]) >= 1


def test_bundle_integration_clean_run(tmp_path: Path) -> None:
    script = tmp_path / "app.py"
    script.write_text(SCRIPT_CLEAN, encoding="utf-8")

    runner.run([sys.executable, str(script)], base=tmp_path)

    run_dir = pai.run.latest_pointer(base=tmp_path)
    bundle = build_bundle(run_dir)

    assert bundle["run"]["exit_code"] == 0
    assert bundle["exceptions"] == []
    assert any(e["imported"] == "os" for e in bundle["imports"])
