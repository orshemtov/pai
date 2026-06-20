"""Tests for the aiobotocore side-effect collector."""

import asyncio
import json
from pathlib import Path

from pai.collectors.side_effects.aiobotocore import (
    AiobotocoreCollector,
    patch_aiobotocore,
)
from pai.events import AiobotocoreEvent
from pai.writer import EventWriter


def read_aiobotocore_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return result

    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "aiobotocore":
            result.append(event)
    return result


class FakeAsyncClient:
    class meta:
        class service_model:
            service_name = "sqs"

    async def _make_api_call(self, operation_name: str, api_params: dict) -> dict:
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


def test_aiobotocore_event_shape() -> None:
    event = AiobotocoreEvent(service="sqs", operation="SendMessage", duration_ms=7)
    result = event.to_dict()

    assert result["event"] == "aiobotocore"
    assert result["service"] == "sqs"
    assert result["operation"] == "SendMessage"
    assert result["duration_ms"] == 7


def test_patch_aiobotocore_emits_event(tmp_path: Path) -> None:
    with EventWriter(tmp_path) as writer:
        collector = AiobotocoreCollector(writer=writer)
        patch_aiobotocore(collector, FakeAsyncClient)

        client = FakeAsyncClient()
        asyncio.run(client._make_api_call("SendMessage", {"QueueUrl": "x"}))

    events = read_aiobotocore_events(tmp_path)

    assert len(events) == 1
    assert events[0]["service"] == "sqs"
    assert events[0]["operation"] == "SendMessage"
