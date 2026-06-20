"""HTTP side-effect collector.

Patches ``requests.Session.request`` and ``httpx.Client.send`` /
``httpx.AsyncClient.send`` to emit ``HttpEvent`` for every outbound request.

Patching is done lazily: called only after the target library has been imported,
so this module is safe to import even when requests/httpx are not installed.
"""

import contextlib
import time
import types
from typing import Any

from pai.events import HttpEvent
from pai.writer import EventWriter

__all__ = [
    "HttpCollector",
    "patch_httpx",
    "patch_httpx_async_client",
    "patch_httpx_sync_client",
    "patch_requests",
]


class HttpCollector:
    """Holds the writer; provides patch methods for each supported HTTP library."""

    def __init__(self, writer: EventWriter) -> None:
        self.writer = writer

    def record(self, method: str, url: str, status_code: int, duration_ms: int) -> None:
        self.writer.write(
            HttpEvent(
                method=method.upper(),
                url=str(url),
                status_code=status_code,
                duration_ms=duration_ms,
            )
        )


def patch_requests(
    collector: HttpCollector,
    requests_module: types.ModuleType,
    session_cls: Any,
) -> None:
    """Wrap ``session_cls.request`` to emit an ``HttpEvent`` on each call."""
    original = session_cls.request

    def patched(self: Any, method: str, url: str, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = original(self, method, url, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(method, url, response.status_code, duration_ms)
        return response

    session_cls.request = patched


def patch_httpx(collector: HttpCollector, httpx_module: types.ModuleType) -> None:
    """Wrap ``httpx.Client.send`` and ``httpx.AsyncClient.send``."""
    with contextlib.suppress(AttributeError):
        patch_httpx_sync_client(collector, httpx_module.Client)

    with contextlib.suppress(AttributeError):
        patch_httpx_async_client(collector, httpx_module.AsyncClient)


def patch_httpx_sync_client(collector: HttpCollector, client_cls: Any) -> None:
    """Wrap sync ``client_cls.send`` to emit an ``HttpEvent``."""
    original_send = client_cls.send

    def patched_send(self: Any, request: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = original_send(self, request, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(request.method, str(request.url), response.status_code, duration_ms)
        return response

    client_cls.send = patched_send


def patch_httpx_async_client(collector: HttpCollector, async_client_cls: Any) -> None:
    """Wrap async ``async_client_cls.send`` to emit an ``HttpEvent``."""
    original_send = async_client_cls.send

    async def patched_send(self: Any, request: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = await original_send(self, request, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(request.method, str(request.url), response.status_code, duration_ms)
        return response

    async_client_cls.send = patched_send
