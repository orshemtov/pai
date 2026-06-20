"""Tests for the anthropic side-effect collector."""

import asyncio
import json
from pathlib import Path
from typing import Any

from pai.collectors.side_effects.anthropic import (
    AnthropicCollector,
    patch_anthropic,
    patch_anthropic_async,
)
from pai.events import AnthropicEvent
from pai.writer import EventWriter


def read_anthropic_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return result

    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "anthropic":
            result.append(event)
    return result


class FakeUsage:
    input_tokens = 20
    output_tokens = 8


class FakeMessage:
    model = "claude-opus-4-8"
    usage = FakeUsage()


def make_messages_cls(async_variant: bool = False) -> type:
    class Messages:
        def create(self, **kwargs: Any) -> FakeMessage:
            return FakeMessage()

    class AsyncMessages:
        async def create(self, **kwargs: Any) -> FakeMessage:
            return FakeMessage()

    if async_variant:
        return AsyncMessages
    return Messages


def test_anthropic_event_shape() -> None:
    event = AnthropicEvent(
        model="claude-opus-4-8",
        input_tokens=100,
        output_tokens=50,
        duration_ms=320,
    )
    result = event.to_dict()

    assert result["event"] == "anthropic"
    assert result["model"] == "claude-opus-4-8"
    assert result["input_tokens"] == 100
    assert result["output_tokens"] == 50


def test_patch_anthropic_emits_event(tmp_path: Path) -> None:
    messages_cls = make_messages_cls()

    with EventWriter(tmp_path) as writer:
        collector = AnthropicCollector(writer=writer)
        patch_anthropic(collector, messages_cls)

        msg = messages_cls()
        msg.create(model="claude-opus-4-8", max_tokens=1024, messages=[])

    events = read_anthropic_events(tmp_path)

    assert len(events) == 1
    assert events[0]["model"] == "claude-opus-4-8"
    assert events[0]["input_tokens"] == 20
    assert events[0]["output_tokens"] == 8


def test_patch_anthropic_async_emits_event(tmp_path: Path) -> None:
    async_cls = make_messages_cls(async_variant=True)

    with EventWriter(tmp_path) as writer:
        collector = AnthropicCollector(writer=writer)
        patch_anthropic_async(collector, async_cls)

        msg = async_cls()
        asyncio.run(msg.create(model="claude-opus-4-8", max_tokens=1024, messages=[]))

    events = read_anthropic_events(tmp_path)

    assert len(events) == 1
    assert events[0]["event"] == "anthropic"
