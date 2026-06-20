"""Tests for the SQLAlchemy side-effect collector."""

import json
from pathlib import Path
from typing import Any

from pai.collectors.side_effects.sqlalchemy import (
    SqlalchemyCollector,
    extract_sql_operation,
    patch_sqlalchemy,
)
from pai.events import SqlalchemyEvent
from pai.writer import EventWriter


def read_sqlalchemy_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return result

    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "sqlalchemy":
            result.append(event)
    return result


def test_sqlalchemy_event_shape() -> None:
    event = SqlalchemyEvent(
        operation="SELECT",
        query="SELECT * FROM users",
        duration_ms=5,
    )
    result = event.to_dict()

    assert result["event"] == "sqlalchemy"
    assert result["schema_version"] == 1
    assert result["operation"] == "SELECT"
    assert result["query"] == "SELECT * FROM users"
    assert result["duration_ms"] == 5


def test_extract_sql_operation() -> None:
    assert extract_sql_operation("SELECT * FROM users") == "SELECT"
    assert extract_sql_operation("  insert into orders values (1)") == "INSERT"
    assert extract_sql_operation("") == "UNKNOWN"


def test_patch_sqlalchemy_emits_event(tmp_path: Path) -> None:
    class FakeResult:
        pass

    class FakeConnection:
        def execute(self, statement: Any, *args: Any, **kwargs: Any) -> FakeResult:
            return FakeResult()

    with EventWriter(tmp_path) as writer:
        collector = SqlalchemyCollector(writer=writer)
        patch_sqlalchemy(collector, FakeConnection)

        conn = FakeConnection()
        conn.execute("SELECT id FROM users WHERE active = true")

    events = read_sqlalchemy_events(tmp_path)

    assert len(events) == 1
    assert events[0]["operation"] == "SELECT"
    assert "SELECT" in events[0]["query"]
    assert isinstance(events[0]["duration_ms"], int)
    assert events[0]["duration_ms"] >= 0
    assert "timestamp" in events[0]
