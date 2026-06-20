"""Tests for AWS side-effect collector.

Uses synthetic botocore-shaped stand-ins — boto3/aiobotocore not required.
"""

import asyncio
import json
from pathlib import Path

from pai.collectors.side_effects.aws import AwsCollector, patch_aiobotocore, patch_botocore
from pai.events import AwsEvent
from pai.writer import EventWriter


def read_aws_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return result
    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "aws":
            result.append(event)
    return result


class FakeServiceModel:
    service_name = "s3"


class FakeMeta:
    service_model = FakeServiceModel()


def make_botocore_cls(service: str = "s3", response: dict | None = None) -> type:
    class _Client:
        class meta:
            class service_model:
                service_name = service

        def _make_api_call(self, operation_name: str, api_params: dict) -> dict:
            return response or {"ResponseMetadata": {"HTTPStatusCode": 200}}

    return _Client


def test_aws_event_shape() -> None:
    event = AwsEvent(service="s3", operation="GetObject", duration_ms=12)
    result = event.to_dict()

    assert result["event"] == "aws"
    assert result["schema_version"] == 1
    assert result["service"] == "s3"
    assert result["operation"] == "GetObject"
    assert result["duration_ms"] == 12


def test_patch_botocore_emits_event(tmp_path: Path) -> None:
    client_cls = make_botocore_cls(service="s3")

    with EventWriter(tmp_path) as writer:
        collector = AwsCollector(writer=writer)
        patch_botocore(collector, client_cls)

        client = client_cls()
        client._make_api_call("GetObject", {"Bucket": "my-bucket", "Key": "file.txt"})

    events = read_aws_events(tmp_path)

    assert len(events) == 1
    assert events[0]["service"] == "s3"
    assert events[0]["operation"] == "GetObject"
    assert isinstance(events[0]["duration_ms"], int)
    assert "timestamp" in events[0]


def test_patch_botocore_records_service_and_operation(tmp_path: Path) -> None:
    client_cls = make_botocore_cls(service="dynamodb")

    with EventWriter(tmp_path) as writer:
        collector = AwsCollector(writer=writer)
        patch_botocore(collector, client_cls)

        client = client_cls()
        client._make_api_call("PutItem", {"TableName": "users", "Item": {}})

    events = read_aws_events(tmp_path)

    assert len(events) == 1
    assert events[0]["service"] == "dynamodb"
    assert events[0]["operation"] == "PutItem"


def test_patch_aiobotocore_emits_event(tmp_path: Path) -> None:
    class AsyncClient:
        class meta:
            class service_model:
                service_name = "sqs"

        async def _make_api_call(self, operation_name: str, api_params: dict) -> dict:
            return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    with EventWriter(tmp_path) as writer:
        collector = AwsCollector(writer=writer)
        patch_aiobotocore(collector, AsyncClient)

        client = AsyncClient()
        asyncio.run(client._make_api_call("SendMessage", {"QueueUrl": "x", "MessageBody": "y"}))

    events = read_aws_events(tmp_path)

    assert len(events) == 1
    assert events[0]["service"] == "sqs"
    assert events[0]["operation"] == "SendMessage"
