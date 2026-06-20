"""boto3 side-effect collector."""

import time
from typing import Any

from pai.events import Boto3Event
from pai.writer import EventWriter

__all__ = ["Boto3Collector", "patch_botocore"]


class Boto3Collector:
    """Records AWS API calls made through boto3's botocore client."""

    def __init__(self, writer: EventWriter) -> None:
        self.writer = writer

    def record(self, service: str, operation: str, duration_ms: int) -> None:
        event = Boto3Event(
            service=service,
            operation=operation,
            duration_ms=duration_ms,
        )
        self.writer.write(event)


def patch_botocore(collector: Boto3Collector, client_cls: Any) -> None:
    """Wrap ``botocore.client.BaseClient._make_api_call``."""
    original = client_cls._make_api_call

    def patched(self: Any, operation_name: str, api_params: dict) -> Any:
        service = self.meta.service_model.service_name
        start = time.monotonic()
        result = original(self, operation_name, api_params)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(service, operation_name, duration_ms)
        return result

    client_cls._make_api_call = patched
