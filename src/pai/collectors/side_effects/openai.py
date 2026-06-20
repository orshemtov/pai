"""openai side-effect collector."""

import time
from typing import Any

from pai.events import OpenaiEvent
from pai.writer import EventWriter

__all__ = ["OpenaiCollector", "patch_openai", "patch_openai_async"]


class OpenaiCollector:
    """Records completion calls made through the openai SDK."""

    def __init__(self, writer: EventWriter) -> None:
        self.writer = writer

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int,
    ) -> None:
        event = OpenaiEvent(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
        )
        self.writer.write(event)


def patch_openai(collector: OpenaiCollector, completions_cls: Any) -> None:
    """Wrap sync ``completions_cls.create``."""
    original = completions_cls.create

    def patched(self: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = original(self, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        collector.record(
            model=response.model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            duration_ms=duration_ms,
        )
        return response

    completions_cls.create = patched


def patch_openai_async(collector: OpenaiCollector, async_completions_cls: Any) -> None:
    """Wrap async ``async_completions_cls.create``."""
    original = async_completions_cls.create

    async def patched(self: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = await original(self, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        collector.record(
            model=response.model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            duration_ms=duration_ms,
        )
        return response

    async_completions_cls.create = patched
