"""Tests for AI provider side-effect collector.

Uses synthetic SDK-shaped stand-ins — openai/anthropic not required.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from pai.collectors.side_effects.ai import (
    AiCollector,
    patch_anthropic,
    patch_anthropic_async,
    patch_openai,
    patch_openai_async,
)
from pai.events import AiEvent
from pai.writer import EventWriter


def read_ai_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return result
    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "ai":
            result.append(event)
    return result


class FakeOpenAIUsage:
    prompt_tokens = 10
    completion_tokens = 5


class FakeChatCompletion:
    model = "gpt-4o"
    usage = FakeOpenAIUsage()


class FakeAnthropicUsage:
    input_tokens = 20
    output_tokens = 8


class FakeAnthropicMessage:
    model = "claude-opus-4-8"
    usage = FakeAnthropicUsage()


def make_openai_completions_cls(model: str = "gpt-4o", async_: bool = False) -> type:
    class Completions:
        def create(self, **kwargs: Any) -> FakeChatCompletion:
            return FakeChatCompletion()

    class AsyncCompletions:
        async def create(self, **kwargs: Any) -> FakeChatCompletion:
            return FakeChatCompletion()

    return AsyncCompletions if async_ else Completions


def make_anthropic_messages_cls(async_: bool = False) -> type:
    class Messages:
        def create(self, **kwargs: Any) -> FakeAnthropicMessage:
            return FakeAnthropicMessage()

    class AsyncMessages:
        async def create(self, **kwargs: Any) -> FakeAnthropicMessage:
            return FakeAnthropicMessage()

    return AsyncMessages if async_ else Messages


def test_ai_event_shape() -> None:
    event = AiEvent(
        provider="openai",
        model="gpt-4o",
        input_tokens=100,
        output_tokens=50,
        duration_ms=320,
    )
    result = event.to_dict()

    assert result["event"] == "ai"
    assert result["schema_version"] == 1
    assert result["provider"] == "openai"
    assert result["model"] == "gpt-4o"
    assert result["input_tokens"] == 100
    assert result["output_tokens"] == 50
    assert result["duration_ms"] == 320


def test_patch_openai_emits_event(tmp_path: Path) -> None:
    completions_cls = make_openai_completions_cls()

    with EventWriter(tmp_path) as writer:
        collector = AiCollector(writer=writer)
        patch_openai(collector, completions_cls)

        comp = completions_cls()
        comp.create(model="gpt-4o", messages=[{"role": "user", "content": "hi"}])

    events = read_ai_events(tmp_path)

    assert len(events) == 1
    assert events[0]["provider"] == "openai"
    assert events[0]["model"] == "gpt-4o"
    assert events[0]["input_tokens"] == 10
    assert events[0]["output_tokens"] == 5
    assert isinstance(events[0]["duration_ms"], int)
    assert "timestamp" in events[0]


def test_patch_openai_async_emits_event(tmp_path: Path) -> None:
    async_cls = make_openai_completions_cls(async_=True)

    with EventWriter(tmp_path) as writer:
        collector = AiCollector(writer=writer)
        patch_openai_async(collector, async_cls)

        comp = async_cls()
        asyncio.run(comp.create(model="gpt-4o", messages=[]))

    events = read_ai_events(tmp_path)

    assert len(events) == 1
    assert events[0]["provider"] == "openai"


def test_patch_anthropic_emits_event(tmp_path: Path) -> None:
    messages_cls = make_anthropic_messages_cls()

    with EventWriter(tmp_path) as writer:
        collector = AiCollector(writer=writer)
        patch_anthropic(collector, messages_cls)

        msg = messages_cls()
        msg.create(model="claude-opus-4-8", max_tokens=1024, messages=[])

    events = read_ai_events(tmp_path)

    assert len(events) == 1
    assert events[0]["provider"] == "anthropic"
    assert events[0]["model"] == "claude-opus-4-8"
    assert events[0]["input_tokens"] == 20
    assert events[0]["output_tokens"] == 8


def test_patch_anthropic_async_emits_event(tmp_path: Path) -> None:
    async_cls = make_anthropic_messages_cls(async_=True)

    with EventWriter(tmp_path) as writer:
        collector = AiCollector(writer=writer)
        patch_anthropic_async(collector, async_cls)

        msg = async_cls()
        asyncio.run(msg.create(model="claude-sonnet-4-6", max_tokens=512, messages=[]))

    events = read_ai_events(tmp_path)

    assert len(events) == 1
    assert events[0]["provider"] == "anthropic"
