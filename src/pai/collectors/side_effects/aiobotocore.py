"""aiobotocore side-effect collector."""

import time
from typing import Any

from pai.events import AiobotocoreEvent
from pai.writer import EventWriter

__all__ = ["AiobotocoreCollector", "patch_aiobotocore"]


class AiobotocoreCollector:
    """Records AWS API calls made through aiobotocore."""

    def __init__(self, writer: EventWriter) -> None:
        self.writer = writer

    def record(self, service: str, operation: str, duration_ms: int) -> None:
        event = AiobotocoreEvent(
            service=service,
            operation=operation,
            duration_ms=duration_ms,
        )
        self.writer.write(event)


def patch_aiobotocore(collector: AiobotocoreCollector, client_cls: Any) -> None:
    """Wrap ``aiobotocore.client.AioBaseClient._make_api_call``."""
    original = client_cls._make_api_call

    async def patched(self: Any, operation_name: str, api_params: dict) -> Any:
        service = self.meta.service_model.service_name
        start = time.monotonic()
        result = await original(self, operation_name, api_params)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(service, operation_name, duration_ms)
        return result

    client_cls._make_api_call = patched
