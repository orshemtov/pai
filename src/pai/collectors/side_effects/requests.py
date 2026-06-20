"""requests side-effect collector."""

import time
import types
from typing import Any

from pai.events import RequestsEvent
from pai.writer import EventWriter

__all__ = ["RequestsCollector", "patch_requests"]


class RequestsCollector:
    """Records outbound calls made through requests."""

    def __init__(self, writer: EventWriter) -> None:
        self.writer = writer

    def record(self, method: str, url: str, status_code: int, duration_ms: int) -> None:
        event = RequestsEvent(
            method=method.upper(),
            url=str(url),
            status_code=status_code,
            duration_ms=duration_ms,
        )
        self.writer.write(event)


def patch_requests(
    collector: RequestsCollector,
    requests_module: types.ModuleType,
    session_cls: Any,
) -> None:
    """Wrap ``requests.Session.request`` to emit one event per request."""
    original = session_cls.request

    def patched(self: Any, method: str, url: str, **kwargs: Any) -> Any:
        start = time.monotonic()
        response = original(self, method, url, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(method, url, response.status_code, duration_ms)
        return response

    session_cls.request = patched
