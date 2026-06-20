"""Tests for SQL side-effect collector.

Uses synthetic stand-ins — SQLAlchemy/asyncpg not required.
"""

import asyncio
import json
import types
from pathlib import Path
from typing import Any

from pai.collectors.side_effects.sql import (
    SqlCollector,
    extract_sql_operation,
    patch_asyncpg,
    patch_sqlalchemy,
)
from pai.events import SqlEvent
from pai.writer import EventWriter


def read_sql_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return result
    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "sql":
            result.append(event)
    return result


def test_sql_event_shape() -> None:
    event = SqlEvent(operation="SELECT", query="SELECT * FROM users", duration_ms=5)
    result = event.to_dict()

    assert result["event"] == "sql"
    assert result["schema_version"] == 1
    assert result["operation"] == "SELECT"
    assert result["query"] == "SELECT * FROM users"
    assert result["duration_ms"] == 5


def test_extract_sql_operation_select() -> None:
    assert extract_sql_operation("SELECT * FROM users") == "SELECT"


def test_extract_sql_operation_insert() -> None:
    assert extract_sql_operation("  insert into orders values (1)") == "INSERT"


def test_extract_sql_operation_empty() -> None:
    assert extract_sql_operation("") == "UNKNOWN"


def test_patch_sqlalchemy_emits_event(tmp_path: Path) -> None:
    fake_sa = types.ModuleType("sqlalchemy")

    class FakeResult:
        pass

    class FakeSAConnection:
        def execute(self, statement: Any, *args: Any, **kwargs: Any) -> FakeResult:
            return FakeResult()

    fake_sa.engine = types.ModuleType("sqlalchemy.engine")  # type: ignore
    fake_sa.engine.base = types.ModuleType("sqlalchemy.engine.base")  # type: ignore
    fake_sa.engine.base.Connection = FakeSAConnection  # type: ignore

    with EventWriter(tmp_path) as writer:
        collector = SqlCollector(writer=writer)
        patch_sqlalchemy(collector, FakeSAConnection)

        conn = FakeSAConnection()
        conn.execute("SELECT id FROM users WHERE active = true")

    events = read_sql_events(tmp_path)

    assert len(events) == 1
    assert events[0]["operation"] == "SELECT"
    assert "SELECT" in events[0]["query"]
    assert isinstance(events[0]["duration_ms"], int)
    assert events[0]["duration_ms"] >= 0
    assert "timestamp" in events[0]


def test_patch_sqlalchemy_records_operation(tmp_path: Path) -> None:
    class FakeSAConnection:
        def execute(self, statement: Any, *args: Any, **kwargs: Any) -> None:
            return None

    with EventWriter(tmp_path) as writer:
        collector = SqlCollector(writer=writer)
        patch_sqlalchemy(collector, FakeSAConnection)

        conn = FakeSAConnection()
        conn.execute("INSERT INTO orders (user_id) VALUES (:id)")

    events = read_sql_events(tmp_path)

    assert len(events) == 1
    assert events[0]["operation"] == "INSERT"


def test_patch_asyncpg_emits_event(tmp_path: Path) -> None:
    class FakeAsyncpgConnection:
        async def execute(self, query: str, *args: Any, **kwargs: Any) -> str:
            return "OK"

    with EventWriter(tmp_path) as writer:
        collector = SqlCollector(writer=writer)
        patch_asyncpg(collector, FakeAsyncpgConnection)

        conn = FakeAsyncpgConnection()
        asyncio.run(conn.execute("DELETE FROM sessions WHERE expired = true"))

    events = read_sql_events(tmp_path)

    assert len(events) == 1
    assert events[0]["operation"] == "DELETE"
    assert events[0]["duration_ms"] >= 0


def test_patch_asyncpg_patches_fetch(tmp_path: Path) -> None:
    class FakeAsyncpgConnection:
        async def fetch(self, query: str, *args: Any, **kwargs: Any) -> list:
            return []

    with EventWriter(tmp_path) as writer:
        collector = SqlCollector(writer=writer)
        patch_asyncpg(collector, FakeAsyncpgConnection)

        conn = FakeAsyncpgConnection()
        asyncio.run(conn.fetch("SELECT * FROM products"))

    events = read_sql_events(tmp_path)

    assert len(events) == 1
    assert events[0]["operation"] == "SELECT"
