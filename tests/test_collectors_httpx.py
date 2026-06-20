"""Tests for the httpx side-effect collector."""

import asyncio
import json
from pathlib import Path
from typing import Any

from pai.collectors.side_effects.httpx import (
    HttpxCollector,
    patch_httpx_async_client,
    patch_httpx_sync_client,
)
from pai.events import HttpxEvent
from pai.writer import EventWriter


def read_httpx_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return result

    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "httpx":
            result.append(event)
    return result


class FakeRequest:
    method = "POST"
    url = "https://example.com/httpx"


class FakeResponse:
    status_code = 201


def test_httpx_event_shape() -> None:
    event = HttpxEvent(
        method="POST",
        url="https://example.com/api",
        status_code=201,
        duration_ms=12,
    )
    result = event.to_dict()

    assert result["event"] == "httpx"
    assert result["method"] == "POST"
    assert result["url"] == "https://example.com/api"
    assert result["status_code"] == 201
    assert result["duration_ms"] == 12


def test_patch_httpx_sync_client_emits_event(tmp_path: Path) -> None:
    class FakeClient:
        def send(self, request: FakeRequest, **kwargs: Any) -> FakeResponse:
            return FakeResponse()

    with EventWriter(tmp_path) as writer:
        collector = HttpxCollector(writer=writer)
        patch_httpx_sync_client(collector, FakeClient)

        FakeClient().send(FakeRequest())

    events = read_httpx_events(tmp_path)

    assert len(events) == 1
    assert events[0]["method"] == "POST"
    assert events[0]["url"] == "https://example.com/httpx"
    assert events[0]["status_code"] == 201


def test_patch_httpx_async_client_emits_event(tmp_path: Path) -> None:
    class FakeAsyncClient:
        async def send(self, request: FakeRequest, **kwargs: Any) -> FakeResponse:
            return FakeResponse()

    with EventWriter(tmp_path) as writer:
        collector = HttpxCollector(writer=writer)
        patch_httpx_async_client(collector, FakeAsyncClient)

        asyncio.run(FakeAsyncClient().send(FakeRequest()))

    events = read_httpx_events(tmp_path)

    assert len(events) == 1
    assert events[0]["event"] == "httpx"
