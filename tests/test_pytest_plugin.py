import json
import os
import subprocess
import sys
from pathlib import Path

from pai import run as run_module

PASSING_TEST = """\
def test_passes():
    assert 1 + 1 == 2
"""

FAILING_TEST = """\
def test_fails():
    assert 1 + 1 == 3
"""

MIXED_TESTS = """\
def test_ok():
    assert True


def test_bad():
    assert False, "intentional"
"""


def run_plugin(tmp_path: Path, test_source: str) -> list[dict]:
    test_file = tmp_path / "test_target.py"
    test_file.write_text(test_source, encoding="utf-8")

    run_dir = run_module.create_run_dir(base=tmp_path)

    env = dict(os.environ)
    env["PAI_RUN_DIR"] = str(run_dir)

    subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-q", "--tb=short"],
        env=env,
        check=False,
    )

    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            result.append(json.loads(line))
    return result


def filter_test_events(events: list[dict]) -> list[dict]:
    result: list[dict] = []
    for e in events:
        if e["event"] == "test":
            result.append(e)
    return result


def test_plugin_records_passing_test(tmp_path: Path) -> None:
    events = run_plugin(tmp_path, PASSING_TEST)
    found = filter_test_events(events)

    assert len(found) == 1
    assert found[0]["outcome"] == "passed"
    assert "test_passes" in found[0]["test_id"]
    assert found[0]["schema_version"] == 1
    assert "timestamp" in found[0]


def test_plugin_records_failing_test(tmp_path: Path) -> None:
    events = run_plugin(tmp_path, FAILING_TEST)
    found = filter_test_events(events)

    assert len(found) == 1
    assert found[0]["outcome"] == "failed"
    assert isinstance(found[0]["message"], str)
    assert len(found[0]["message"]) > 0


def test_plugin_records_duration(tmp_path: Path) -> None:
    events = run_plugin(tmp_path, PASSING_TEST)
    found = filter_test_events(events)

    assert len(found) == 1
    assert isinstance(found[0]["duration_ms"], int)
    assert found[0]["duration_ms"] >= 0


def test_plugin_records_file(tmp_path: Path) -> None:
    events = run_plugin(tmp_path, PASSING_TEST)
    found = filter_test_events(events)

    assert len(found) == 1
    assert found[0]["file"].endswith(".py")


def test_plugin_records_multiple_tests(tmp_path: Path) -> None:
    events = run_plugin(tmp_path, MIXED_TESTS)
    found = filter_test_events(events)

    assert len(found) == 2

    outcomes: list[str] = []
    for e in found:
        outcomes.append(e["outcome"])

    assert "passed" in outcomes
    assert "failed" in outcomes


def test_plugin_noop_without_run_dir(tmp_path: Path) -> None:
    test_file = tmp_path / "test_noop.py"
    test_file.write_text(PASSING_TEST, encoding="utf-8")

    env = {k: v for k, v in os.environ.items() if k != "PAI_RUN_DIR"}

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-q", "--tb=short"],
        env=env,
        check=False,
        capture_output=True,
    )

    assert result.returncode == 0
    assert not (tmp_path / ".pai").exists()
