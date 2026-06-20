from pai.events import CallEvent, ExceptionEvent, ImportEvent, RunEndEvent, RunStartEvent, TestEvent


def test_exception_event_to_dict_matches_expected_shape() -> None:
    event = ExceptionEvent(
        symbol="main.parse_user",
        file="main.py",
        line=2,
        exception_type="KeyError",
        message="'user_id'",
        locals_schema={"payload": {"type": "dict", "keys": ["name"]}},
    )

    assert event.to_dict() == {
        "event": "exception",
        "schema_version": 1,
        "symbol": "main.parse_user",
        "file": "main.py",
        "line": 2,
        "exception_type": "KeyError",
        "message": "'user_id'",
        "locals_schema": {"payload": {"type": "dict", "keys": ["name"]}},
    }


def test_import_event_to_dict() -> None:
    event = ImportEvent(module="app.orders", imported="app.db")

    assert event.to_dict() == {
        "event": "import",
        "schema_version": 1,
        "module": "app.orders",
        "imported": "app.db",
    }


def test_run_start_event_to_dict() -> None:
    event = RunStartEvent(
        command=["python", "main.py"],
        cwd="/tmp",
        python_version="3.13.0",
    )

    result = event.to_dict()

    assert result["event"] == "run_start"
    assert result["schema_version"] == 1
    assert result["command"] == ["python", "main.py"]
    assert result["cwd"] == "/tmp"
    assert result["python_version"] == "3.13.0"


def test_test_event_to_dict() -> None:
    event = TestEvent(
        test_id="tests/test_foo.py::test_bar",
        outcome="failed",
        duration_ms=12,
        file="tests/test_foo.py",
        message="AssertionError: assert 1 == 2",
    )

    result = event.to_dict()

    assert result["event"] == "test"
    assert result["schema_version"] == 1
    assert result["test_id"] == "tests/test_foo.py::test_bar"
    assert result["outcome"] == "failed"
    assert result["duration_ms"] == 12
    assert result["file"] == "tests/test_foo.py"
    assert result["message"] == "AssertionError: assert 1 == 2"


def test_call_event_to_dict() -> None:
    event = CallEvent(
        caller="app.main.main",
        callee="app.orders.process",
        file="app/orders.py",
        line=10,
        duration_ms=3,
    )

    result = event.to_dict()

    assert result["event"] == "call"
    assert result["schema_version"] == 1
    assert result["caller"] == "app.main.main"
    assert result["callee"] == "app.orders.process"
    assert result["file"] == "app/orders.py"
    assert result["line"] == 10
    assert result["duration_ms"] == 3


def test_run_end_event_to_dict() -> None:
    event = RunEndEvent(exit_code=1, duration_ms=42)

    result = event.to_dict()

    assert result["event"] == "run_end"
    assert result["schema_version"] == 1
    assert result["exit_code"] == 1
    assert result["duration_ms"] == 42
