"""anthropic side-effect collector."""

import time
from typing import Any

from pai.events import AnthropicEvent
from pai.writer import EventWriter

__all__ = ["AnthropicCollector", "patch_anthropic", "patch_anthropic_async"]


class AnthropicCollector:
    """Records message calls made through the anthropic SDK."""

    def __init__(self, writer: EventWriter) -> None:
        self.writer = writer

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int,
    ) -> None:
        event = AnthropicEvent(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
        )
        self.writer.write(event)


def patch_anthropic(collector: AnthropicCollector, messages_cls: Any) -> None:
    """Wrap sync ``messages_cls.create``."""
    original = messages_cls.create

    def patched(self: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = original(self, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        collector.record(
            model=response.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            duration_ms=duration_ms,
        )
        return response

    messages_cls.create = patched


def patch_anthropic_async(collector: AnthropicCollector, async_messages_cls: Any) -> None:
    """Wrap async ``async_messages_cls.create``."""
    original = async_messages_cls.create

    async def patched(self: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = await original(self, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        collector.record(
            model=response.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            duration_ms=duration_ms,
        )
        return response

    async_messages_cls.create = patched
