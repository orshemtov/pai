"""Tests for the HTTP side-effect collector.

Injects synthetic session stand-ins to avoid needing requests/httpx installed.
Each test creates a fresh class via ``make_session_cls`` to prevent cross-test
state pollution from monkey-patching.
"""

import json
import time
import types
from pathlib import Path
from typing import Any

from pai.collectors.side_effects.http import HttpCollector, patch_requests
from pai.events import HttpEvent
from pai.writer import EventWriter


def read_http_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return result
    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "http":
            result.append(event)
    return result


class FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code


def make_session_cls(status_code: int = 200, sleep_secs: float = 0.0) -> type:
    """Return a fresh session class each time — avoids cross-test state pollution."""

    class _Session:
        def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
            if sleep_secs:
                time.sleep(sleep_secs)
            return FakeResponse(status_code)

    return _Session


def test_http_event_shape() -> None:
    event = HttpEvent(
        method="GET",
        url="https://example.com/api",
        status_code=200,
        duration_ms=42,
    )
    result = event.to_dict()

    assert result["event"] == "http"
    assert result["schema_version"] == 1
    assert result["method"] == "GET"
    assert result["url"] == "https://example.com/api"
    assert result["status_code"] == 200
    assert result["duration_ms"] == 42


def test_patch_requests_emits_http_event(tmp_path: Path) -> None:
    fake_requests = types.ModuleType("requests")
    session_cls = make_session_cls(status_code=200)

    with EventWriter(tmp_path) as writer:
        collector = HttpCollector(writer=writer)
        patch_requests(collector, fake_requests, session_cls)

        session_cls().request("GET", "https://example.com/test")

    events = read_http_events(tmp_path)

    assert len(events) == 1
    assert events[0]["method"] == "GET"
    assert events[0]["url"] == "https://example.com/test"
    assert events[0]["status_code"] == 200
    assert events[0]["duration_ms"] >= 0
    assert "timestamp" in events[0]


def test_patch_requests_records_duration(tmp_path: Path) -> None:
    fake_requests = types.ModuleType("requests")
    session_cls = make_session_cls(sleep_secs=0.05)

    with EventWriter(tmp_path) as writer:
        collector = HttpCollector(writer=writer)
        patch_requests(collector, fake_requests, session_cls)

        session_cls().request("GET", "https://example.com")

    events = read_http_events(tmp_path)

    assert len(events) == 1
    assert events[0]["duration_ms"] >= 40


def test_patch_requests_records_non_200_status(tmp_path: Path) -> None:
    fake_requests = types.ModuleType("requests")
    session_cls = make_session_cls(status_code=404)

    with EventWriter(tmp_path) as writer:
        collector = HttpCollector(writer=writer)
        patch_requests(collector, fake_requests, session_cls)

        session_cls().request("POST", "https://example.com/missing")

    events = read_http_events(tmp_path)

    assert len(events) == 1
    assert events[0]["status_code"] == 404
    assert events[0]["method"] == "POST"
