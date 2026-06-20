"""asyncpg side-effect collector."""

import time
from typing import Any

from pai.events import AsyncpgEvent
from pai.writer import EventWriter

__all__ = [
    "AsyncpgCollector",
    "extract_sql_operation",
    "patch_asyncpg",
    "patch_asyncpg_execute",
    "patch_asyncpg_fetch",
    "patch_asyncpg_fetchrow",
    "patch_asyncpg_fetchval",
]


def extract_sql_operation(query: str) -> str:
    """Return the first word of a SQL query as the operation name."""
    stripped = query.strip()
    if not stripped:
        return "UNKNOWN"
    return stripped.split()[0].upper()


class AsyncpgCollector:
    """Records SQL statements executed through asyncpg."""

    def __init__(self, writer: EventWriter) -> None:
        self.writer = writer

    def record(self, query: str, duration_ms: int) -> None:
        event = AsyncpgEvent(
            operation=extract_sql_operation(query),
            query=query,
            duration_ms=duration_ms,
        )
        self.writer.write(event)


def patch_asyncpg(collector: AsyncpgCollector, connection_cls: Any) -> None:
    """Wrap all async query methods on ``connection_cls``."""
    patch_asyncpg_execute(collector, connection_cls)
    patch_asyncpg_fetch(collector, connection_cls)
    patch_asyncpg_fetchrow(collector, connection_cls)
    patch_asyncpg_fetchval(collector, connection_cls)


def patch_asyncpg_execute(collector: AsyncpgCollector, connection_cls: Any) -> None:
    """Wrap ``connection_cls.execute``."""
    try:
        original = connection_cls.execute
    except AttributeError:
        return

    async def patched(self: Any, query: str, *args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        result = await original(self, query, *args, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(query, duration_ms)
        return result

    connection_cls.execute = patched


def patch_asyncpg_fetch(collector: AsyncpgCollector, connection_cls: Any) -> None:
    """Wrap ``connection_cls.fetch``."""
    try:
        original = connection_cls.fetch
    except AttributeError:
        return

    async def patched(self: Any, query: str, *args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        result = await original(self, query, *args, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(query, duration_ms)
        return result

    connection_cls.fetch = patched


def patch_asyncpg_fetchrow(collector: AsyncpgCollector, connection_cls: Any) -> None:
    """Wrap ``connection_cls.fetchrow``."""
    try:
        original = connection_cls.fetchrow
    except AttributeError:
        return

    async def patched(self: Any, query: str, *args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        result = await original(self, query, *args, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(query, duration_ms)
        return result

    connection_cls.fetchrow = patched


def patch_asyncpg_fetchval(collector: AsyncpgCollector, connection_cls: Any) -> None:
    """Wrap ``connection_cls.fetchval``."""
    try:
        original = connection_cls.fetchval
    except AttributeError:
        return

    async def patched(self: Any, query: str, *args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        result = await original(self, query, *args, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(query, duration_ms)
        return result

    connection_cls.fetchval = patched
