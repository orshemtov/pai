"""AWS side-effect collector.

Patches ``botocore.client.BaseClient._make_api_call`` (sync) and
``aiobotocore.client.AioBaseClient._make_api_call`` (async) to emit
``AwsEvent`` for every AWS API call.

Service name is read from ``self.meta.service_model.service_name``, which is
the standard botocore client attribute — works for boto3 and aioboto3.
"""

import time
from typing import Any

from pai.events import AwsEvent
from pai.writer import EventWriter

__all__ = ["AwsCollector", "patch_aiobotocore", "patch_botocore"]


class AwsCollector:
    """Holds the writer; provides patch methods for botocore client classes."""

    def __init__(self, writer: EventWriter) -> None:
        self.writer = writer

    def record(self, service: str, operation: str, duration_ms: int) -> None:
        self.writer.write(AwsEvent(service=service, operation=operation, duration_ms=duration_ms))


def patch_botocore(collector: AwsCollector, client_cls: Any) -> None:
    """Wrap ``client_cls._make_api_call`` to emit an ``AwsEvent`` per call."""
    original = client_cls._make_api_call

    def patched(self: Any, operation_name: str, api_params: dict) -> Any:
        service = self.meta.service_model.service_name
        start = time.monotonic()
        result = original(self, operation_name, api_params)
        collector.record(service, operation_name, int((time.monotonic() - start) * 1000))
        return result

    client_cls._make_api_call = patched


def patch_aiobotocore(collector: AwsCollector, client_cls: Any) -> None:
    """Wrap async ``client_cls._make_api_call`` to emit an ``AwsEvent`` per call."""
    original = client_cls._make_api_call

    async def patched(self: Any, operation_name: str, api_params: dict) -> Any:
        service = self.meta.service_model.service_name
        start = time.monotonic()
        result = await original(self, operation_name, api_params)
        collector.record(service, operation_name, int((time.monotonic() - start) * 1000))
        return result

    client_cls._make_api_call = patched
