import subprocess
import sys
from pathlib import Path


def event_names(events: list[dict]) -> list[str]:
    names: list[str] = []
    for event in events:
        names.append(str(event["event"]))
    return names


def test_example_projects_include_docs_and_mise_tasks(
    pure_python_example: Path,
    fastapi_example: Path,
) -> None:
    expected_files = [
        pure_python_example / "pyproject.toml",
        pure_python_example / "mise.toml",
        pure_python_example / "README.md",
        pure_python_example / "demo.py",
        fastapi_example / "pyproject.toml",
        fastapi_example / "mise.toml",
        fastapi_example / "README.md",
        fastapi_example / "demo.py",
    ]

    for path in expected_files:
        assert path.exists(), path


def test_pure_python_failure_example_emits_structured_events(
    pure_python_example: Path,
    pai_command: Path,
    read_events,
) -> None:
    result = subprocess.run(
        [
            str(pai_command),
            "run",
            sys.executable,
            "scripts/failing_order.py",
        ],
        cwd=pure_python_example,
        check=False,
        timeout=15,
    )

    assert result.returncode != 0

    latest = pure_python_example / ".pai" / "runs" / "latest"
    events = read_events(latest / "events.jsonl")
    names = event_names(events)

    assert names[0] == "run_start"
    assert "import" in names
    assert "call" in names
    assert "exception" in names
    assert names[-1] == "run_end"

    exceptions: list[dict] = []
    for event in events:
        if event["event"] == "exception":
            exceptions.append(event)

    assert len(exceptions) == 1
    exception = exceptions[0]
    assert exception["exception_type"] == "KeyError"
    assert exception["locals_schema"]["payload"]["type"] == "dict"
    assert "customer_name" in exception["locals_schema"]["payload"]["keys"]


def test_pure_python_pytest_example_emits_test_events(
    pure_python_example: Path,
    pai_command: Path,
    read_events,
) -> None:
    result = subprocess.run(
        [
            str(pai_command),
            "run",
            sys.executable,
            "-m",
            "pytest",
            "tests/test_orders.py",
        ],
        cwd=pure_python_example,
        env={"PYTHONPATH": str(pure_python_example)},
        check=False,
        timeout=15,
    )

    assert result.returncode != 0

    latest = pure_python_example / ".pai" / "runs" / "latest"
    events = read_events(latest / "events.jsonl")

    test_events: list[dict] = []
    for event in events:
        if event["event"] == "test":
            test_events.append(event)

    outcomes: list[str] = []
    for event in test_events:
        outcomes.append(str(event["outcome"]))

    assert outcomes == ["passed", "failed"]
    assert "test_build_receipt_calculates_total" in test_events[0]["test_id"]
    assert "test_intentional_failure_demonstrates_pai_test_event" in test_events[1]["test_id"]
    assert "AssertionError" in test_events[1]["message"]
