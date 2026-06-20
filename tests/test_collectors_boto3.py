"""Tests for the boto3 side-effect collector."""

import json
from pathlib import Path

from pai.collectors.side_effects.boto3 import Boto3Collector, patch_botocore
from pai.events import Boto3Event
from pai.writer import EventWriter


def read_boto3_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return result

    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "boto3":
            result.append(event)
    return result


def make_client_cls(service: str = "s3", response: dict | None = None) -> type:
    class FakeClient:
        class meta:
            class service_model:
                service_name = service

        def _make_api_call(self, operation_name: str, api_params: dict) -> dict:
            return response or {"ResponseMetadata": {"HTTPStatusCode": 200}}

    return FakeClient


def test_boto3_event_shape() -> None:
    event = Boto3Event(service="s3", operation="GetObject", duration_ms=12)
    result = event.to_dict()

    assert result["event"] == "boto3"
    assert result["schema_version"] == 1
    assert result["service"] == "s3"
    assert result["operation"] == "GetObject"
    assert result["duration_ms"] == 12


def test_patch_botocore_emits_event(tmp_path: Path) -> None:
    client_cls = make_client_cls(service="s3")

    with EventWriter(tmp_path) as writer:
        collector = Boto3Collector(writer=writer)
        patch_botocore(collector, client_cls)

        client = client_cls()
        client._make_api_call("GetObject", {"Bucket": "my-bucket", "Key": "file.txt"})

    events = read_boto3_events(tmp_path)

    assert len(events) == 1
    assert events[0]["service"] == "s3"
    assert events[0]["operation"] == "GetObject"
    assert isinstance(events[0]["duration_ms"], int)
    assert "timestamp" in events[0]
