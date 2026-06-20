import json
import sys
from pathlib import Path

from pai.cli import main


def write_events(run_dir: Path, events: list[dict]) -> None:
    lines: list[str] = []
    for event in events:
        lines.append(json.dumps(event))
    (run_dir / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_run_dir(tmp_path: Path) -> Path:
    run_dir = tmp_path / ".pai" / "runs" / "20260620T120000-abc12345"
    run_dir.mkdir(parents=True)
    write_events(
        run_dir,
        [
            {
                "event_id": "evt_000001",
                "event": "run_start",
                "command": ["python", "app.py"],
                "cwd": "/work",
                "python_version": "3.13",
            },
            {
                "event_id": "evt_000002",
                "event": "exception",
                "symbol": "app.main",
                "file": "app.py",
                "line": 1,
                "exception_type": "RuntimeError",
                "message": "boom",
                "locals_schema": {},
            },
            {
                "event_id": "evt_000002a",
                "event": "call",
                "caller": "__main__",
                "callee": "app.main",
                "file": "app.py",
                "line": 1,
                "duration_ms": 1,
            },
            {
                "event_id": "evt_000003",
                "event": "run_end",
                "exit_code": 1,
                "duration_ms": 8,
            },
        ],
    )
    return run_dir


def test_cli_query_status_prints_json(capsys, tmp_path: Path) -> None:
    run_dir = make_run_dir(tmp_path)

    exit_code = main(["query", "status", "--run", str(run_dir)])

    assert exit_code == 0

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert output["run_id"] == "20260620T120000-abc12345"
    assert output["exit_code"] == 1
    assert output["top_failure"]["event_id"] == "evt_000002"


def test_cli_query_timeline_accepts_limit(capsys, tmp_path: Path) -> None:
    run_dir = make_run_dir(tmp_path)

    exit_code = main(["query", "timeline", "--run", str(run_dir), "--limit", "2"])

    assert exit_code == 0

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert output["limit"] == 2
    assert len(output["events"]) == 2


def test_cli_run_summary_json_prints_compact_status(capsys, monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "app.py"
    script.write_text("answer = 42\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["run", "--summary-json", sys.executable, str(script)])

    assert exit_code == 0

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert output["run_id"]
    assert output["exit_code"] == 0
    assert output["event_counts"]["run_start"] == 1
    assert output["event_counts"]["run_end"] == 1


def test_cli_query_symbol_filters_by_name(capsys, tmp_path: Path) -> None:
    run_dir = make_run_dir(tmp_path)

    exit_code = main(["query", "symbol", "--run", str(run_dir), "--name", "app.main"])

    assert exit_code == 0

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert output["name"] == "app.main"
    assert output["exceptions"][0]["event_id"] == "evt_000002"
    assert output["calls"][0]["event_id"] == "evt_000002a"


def test_cli_query_repair_context_accepts_event_id(capsys, tmp_path: Path) -> None:
    run_dir = make_run_dir(tmp_path)

    exit_code = main(["query", "repair-context", "--run", str(run_dir), "--event", "evt_000002"])

    assert exit_code == 0

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert output["event"]["event_id"] == "evt_000002"
    assert output["symbol"] == "app.main"
