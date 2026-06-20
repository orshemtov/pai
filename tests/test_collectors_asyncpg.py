"""Tests for the asyncpg side-effect collector."""

import asyncio
import json
from pathlib import Path
from typing import Any

from pai.collectors.side_effects.asyncpg import (
    AsyncpgCollector,
    extract_sql_operation,
    patch_asyncpg,
)
from pai.events import AsyncpgEvent
from pai.writer import EventWriter


def read_asyncpg_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return result

    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "asyncpg":
            result.append(event)
    return result


def test_asyncpg_event_shape() -> None:
    event = AsyncpgEvent(
        operation="DELETE",
        query="DELETE FROM sessions",
        duration_ms=5,
    )
    result = event.to_dict()

    assert result["event"] == "asyncpg"
    assert result["operation"] == "DELETE"
    assert result["query"] == "DELETE FROM sessions"
    assert result["duration_ms"] == 5


def test_extract_sql_operation() -> None:
    assert extract_sql_operation("select 1") == "SELECT"
    assert extract_sql_operation("") == "UNKNOWN"


def test_patch_asyncpg_emits_event(tmp_path: Path) -> None:
    class FakeConnection:
        async def execute(self, query: str, *args: Any, **kwargs: Any) -> str:
            return "OK"

    with EventWriter(tmp_path) as writer:
        collector = AsyncpgCollector(writer=writer)
        patch_asyncpg(collector, FakeConnection)

        conn = FakeConnection()
        asyncio.run(conn.execute("DELETE FROM sessions WHERE expired = true"))

    events = read_asyncpg_events(tmp_path)

    assert len(events) == 1
    assert events[0]["operation"] == "DELETE"
    assert events[0]["duration_ms"] >= 0


def test_patch_asyncpg_patches_fetch(tmp_path: Path) -> None:
    class FakeConnection:
        async def fetch(self, query: str, *args: Any, **kwargs: Any) -> list:
            return []

    with EventWriter(tmp_path) as writer:
        collector = AsyncpgCollector(writer=writer)
        patch_asyncpg(collector, FakeConnection)

        conn = FakeConnection()
        asyncio.run(conn.fetch("SELECT * FROM users"))

    events = read_asyncpg_events(tmp_path)

    assert len(events) == 1
    assert events[0]["operation"] == "SELECT"
