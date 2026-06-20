"""Tests for the openai side-effect collector."""

import asyncio
import json
from pathlib import Path
from typing import Any

from pai.collectors.side_effects.openai import OpenaiCollector, patch_openai, patch_openai_async
from pai.events import OpenaiEvent
from pai.writer import EventWriter


def read_openai_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return result

    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "openai":
            result.append(event)
    return result


class FakeUsage:
    prompt_tokens = 10
    completion_tokens = 5


class FakeChatCompletion:
    model = "gpt-4o"
    usage = FakeUsage()


def make_completions_cls(async_variant: bool = False) -> type:
    class Completions:
        def create(self, **kwargs: Any) -> FakeChatCompletion:
            return FakeChatCompletion()

    class AsyncCompletions:
        async def create(self, **kwargs: Any) -> FakeChatCompletion:
            return FakeChatCompletion()

    if async_variant:
        return AsyncCompletions
    return Completions


def test_openai_event_shape() -> None:
    event = OpenaiEvent(
        model="gpt-4o",
        input_tokens=100,
        output_tokens=50,
        duration_ms=320,
    )
    result = event.to_dict()

    assert result["event"] == "openai"
    assert result["model"] == "gpt-4o"
    assert result["input_tokens"] == 100
    assert result["output_tokens"] == 50


def test_patch_openai_emits_event(tmp_path: Path) -> None:
    completions_cls = make_completions_cls()

    with EventWriter(tmp_path) as writer:
        collector = OpenaiCollector(writer=writer)
        patch_openai(collector, completions_cls)

        comp = completions_cls()
        comp.create(model="gpt-4o", messages=[{"role": "user", "content": "hi"}])

    events = read_openai_events(tmp_path)

    assert len(events) == 1
    assert events[0]["model"] == "gpt-4o"
    assert events[0]["input_tokens"] == 10
    assert events[0]["output_tokens"] == 5


def test_patch_openai_async_emits_event(tmp_path: Path) -> None:
    async_cls = make_completions_cls(async_variant=True)

    with EventWriter(tmp_path) as writer:
        collector = OpenaiCollector(writer=writer)
        patch_openai_async(collector, async_cls)

        comp = async_cls()
        asyncio.run(comp.create(model="gpt-4o", messages=[]))

    events = read_openai_events(tmp_path)

    assert len(events) == 1
    assert events[0]["event"] == "openai"
