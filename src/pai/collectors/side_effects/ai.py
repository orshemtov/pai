"""AI provider side-effect collector.

Patches the ``create`` method on chat-completion / messages classes from the
openai and anthropic Python SDKs to emit ``AiEvent`` with model and token usage.

Sync and async variants are handled separately since they require different
wrapping (regular function vs coroutine).
"""

import time
from typing import Any

from pai.events import AiEvent
from pai.writer import EventWriter

__all__ = [
    "AiCollector",
    "patch_anthropic",
    "patch_anthropic_async",
    "patch_openai",
    "patch_openai_async",
]


class AiCollector:
    """Holds the writer; provides patch methods for each supported AI SDK."""

    def __init__(self, writer: EventWriter) -> None:
        self.writer = writer

    def record(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int,
    ) -> None:
        self.writer.write(
            AiEvent(
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
            )
        )


def patch_openai(collector: AiCollector, completions_cls: Any) -> None:
    """Wrap sync ``completions_cls.create`` to emit an ``AiEvent``."""
    original = completions_cls.create

    def patched(self: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = original(self, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        collector.record(
            provider="openai",
            model=response.model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            duration_ms=duration_ms,
        )
        return response

    completions_cls.create = patched


def patch_openai_async(collector: AiCollector, async_completions_cls: Any) -> None:
    """Wrap async ``async_completions_cls.create`` to emit an ``AiEvent``."""
    original = async_completions_cls.create

    async def patched(self: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = await original(self, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        collector.record(
            provider="openai",
            model=response.model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            duration_ms=duration_ms,
        )
        return response

    async_completions_cls.create = patched


def patch_anthropic(collector: AiCollector, messages_cls: Any) -> None:
    """Wrap sync ``messages_cls.create`` to emit an ``AiEvent``."""
    original = messages_cls.create

    def patched(self: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = original(self, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        collector.record(
            provider="anthropic",
            model=response.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            duration_ms=duration_ms,
        )
        return response

    messages_cls.create = patched


def patch_anthropic_async(collector: AiCollector, async_messages_cls: Any) -> None:
    """Wrap async ``async_messages_cls.create`` to emit an ``AiEvent``."""
    original = async_messages_cls.create

    async def patched(self: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = await original(self, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        collector.record(
            provider="anthropic",
            model=response.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            duration_ms=duration_ms,
        )
        return response

    async_messages_cls.create = patched
