"""httpx side-effect collector."""

import contextlib
import time
import types
from typing import Any

from pai.events import HttpxEvent
from pai.writer import EventWriter

__all__ = ["HttpxCollector", "patch_httpx", "patch_httpx_async_client", "patch_httpx_sync_client"]


class HttpxCollector:
    """Records outbound calls made through httpx."""

    def __init__(self, writer: EventWriter) -> None:
        self.writer = writer

    def record(self, method: str, url: str, status_code: int, duration_ms: int) -> None:
        event = HttpxEvent(
            method=method.upper(),
            url=str(url),
            status_code=status_code,
            duration_ms=duration_ms,
        )
        self.writer.write(event)


def patch_httpx(collector: HttpxCollector, httpx_module: types.ModuleType) -> None:
    """Wrap ``httpx.Client.send`` and ``httpx.AsyncClient.send``."""
    with contextlib.suppress(AttributeError):
        patch_httpx_sync_client(collector, httpx_module.Client)

    with contextlib.suppress(AttributeError):
        patch_httpx_async_client(collector, httpx_module.AsyncClient)


def patch_httpx_sync_client(collector: HttpxCollector, client_cls: Any) -> None:
    """Wrap sync ``client_cls.send``."""
    original_send = client_cls.send

    def patched_send(self: Any, request: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = original_send(self, request, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(request.method, str(request.url), response.status_code, duration_ms)
        return response

    client_cls.send = patched_send


def patch_httpx_async_client(collector: HttpxCollector, async_client_cls: Any) -> None:
    """Wrap async ``async_client_cls.send``."""
    original_send = async_client_cls.send

    async def patched_send(self: Any, request: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = await original_send(self, request, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(request.method, str(request.url), response.status_code, duration_ms)
        return response

    async_client_cls.send = patched_send
