import json
from pathlib import Path

from pai.query import (
    build_effects,
    build_failures,
    build_repair_context,
    build_status,
    build_symbol,
    build_tests,
    build_timeline,
)


def write_events(run_dir: Path, events: list[dict]) -> None:
    lines: list[str] = []
    for event in events:
        lines.append(json.dumps(event))
    (run_dir / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def sample_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / ".pai" / "runs" / "20260620T120000-abc12345"
    run_dir.mkdir(parents=True)
    write_events(
        run_dir,
        [
            {
                "event_id": "evt_000001",
                "event": "run_start",
                "schema_version": 1,
                "command": ["python", "app.py"],
                "cwd": "/work",
                "python_version": "3.13",
            },
            {
                "event_id": "evt_000002",
                "event": "test",
                "schema_version": 1,
                "test_id": "tests/test_app.py::test_ok",
                "outcome": "passed",
                "duration_ms": 4,
                "file": "tests/test_app.py",
                "message": "",
            },
            {
                "event_id": "evt_000003",
                "event": "test",
                "schema_version": 1,
                "test_id": "tests/test_app.py::test_bad",
                "outcome": "failed",
                "duration_ms": 9,
                "file": "tests/test_app.py",
                "message": "AssertionError: assert 1 == 2",
            },
            {
                "event_id": "evt_000004",
                "event": "exception",
                "schema_version": 1,
                "symbol": "app.parse",
                "file": "app.py",
                "line": 7,
                "exception_type": "KeyError",
                "message": "'user_id'",
                "locals_schema": {"payload": {"type": "dict", "keys": ["name"]}},
            },
            {
                "event_id": "evt_000004a",
                "event": "call",
                "schema_version": 1,
                "caller": "__main__",
                "callee": "app.parse",
                "file": "app.py",
                "line": 7,
                "duration_ms": 1,
            },
            {
                "event_id": "evt_000005",
                "event": "requests",
                "schema_version": 1,
                "method": "GET",
                "url": "https://api.example.test/users",
                "status_code": 500,
                "duration_ms": 31,
            },
            {
                "event_id": "evt_000006",
                "event": "sqlalchemy",
                "schema_version": 1,
                "operation": "SELECT",
                "query": "SELECT * FROM users",
                "duration_ms": 2,
            },
            {
                "event_id": "evt_000007",
                "event": "run_end",
                "schema_version": 1,
                "exit_code": 1,
                "duration_ms": 120,
            },
        ],
    )
    return run_dir


def test_build_status_returns_compact_run_summary(tmp_path: Path) -> None:
    status = build_status(sample_run(tmp_path))

    assert status == {
        "schema_version": 1,
        "run_id": "20260620T120000-abc12345",
        "command": ["python", "app.py"],
        "cwd": "/work",
        "exit_code": 1,
        "duration_ms": 120,
        "event_counts": {
            "call": 1,
            "exception": 1,
            "requests": 1,
            "run_end": 1,
            "run_start": 1,
            "sqlalchemy": 1,
            "test": 2,
        },
        "failed_tests": 1,
        "exceptions": 1,
        "top_failure": {
            "event_id": "evt_000003",
            "kind": "test",
            "test_id": "tests/test_app.py::test_bad",
            "message": "AssertionError: assert 1 == 2",
        },
    }


def test_build_status_resolves_latest_symlink_run_id(tmp_path: Path) -> None:
    run_dir = sample_run(tmp_path)
    latest = run_dir.parent / "latest"
    latest.symlink_to(run_dir)

    status = build_status(latest)

    assert status["run_id"] == "20260620T120000-abc12345"


def test_build_failures_returns_failed_tests_and_exceptions(tmp_path: Path) -> None:
    failures = build_failures(sample_run(tmp_path))

    assert failures["schema_version"] == 1
    assert failures["run_id"] == "20260620T120000-abc12345"
    assert len(failures["failed_tests"]) == 1
    assert failures["failed_tests"][0]["event_id"] == "evt_000003"
    assert len(failures["exceptions"]) == 1
    assert failures["exceptions"][0]["symbol"] == "app.parse"


def test_build_tests_groups_test_outcomes(tmp_path: Path) -> None:
    tests = build_tests(sample_run(tmp_path))

    assert tests["summary"] == {"passed": 1, "failed": 1}
    assert len(tests["tests"]) == 2


def test_build_effects_groups_by_concrete_package(tmp_path: Path) -> None:
    effects = build_effects(sample_run(tmp_path))

    assert effects["summary"] == {"requests": 1, "sqlalchemy": 1}
    assert effects["packages"]["requests"][0]["event_id"] == "evt_000005"
    assert effects["packages"]["sqlalchemy"][0]["operation"] == "SELECT"


def test_build_timeline_returns_limited_events(tmp_path: Path) -> None:
    timeline = build_timeline(sample_run(tmp_path), limit=3)

    assert timeline["limit"] == 3
    assert len(timeline["events"]) == 3
    assert timeline["events"][0]["event_id"] == "evt_000001"
    assert timeline["events"][2]["event_id"] == "evt_000003"


def test_build_symbol_returns_events_for_named_symbol(tmp_path: Path) -> None:
    symbol = build_symbol(sample_run(tmp_path), name="app.parse")

    assert symbol["schema_version"] == 1
    assert symbol["run_id"] == "20260620T120000-abc12345"
    assert symbol["name"] == "app.parse"
    assert len(symbol["exceptions"]) == 1
    assert symbol["exceptions"][0]["event_id"] == "evt_000004"
    assert len(symbol["calls"]) == 1
    assert symbol["calls"][0]["event_id"] == "evt_000004a"


def test_build_repair_context_returns_failure_slice(tmp_path: Path) -> None:
    context = build_repair_context(sample_run(tmp_path), event_id="evt_000004")

    assert context["schema_version"] == 1
    assert context["run_id"] == "20260620T120000-abc12345"
    assert context["event"]["event_id"] == "evt_000004"
    assert context["symbol"] == "app.parse"
    assert context["related_calls"][0]["event_id"] == "evt_000004a"
    assert context["related_tests"][0]["event_id"] == "evt_000003"
    assert context["recent_effects"][0]["event_id"] == "evt_000005"
