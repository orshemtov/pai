"""SQL side-effect collector.

Patches ``Connection.execute`` (and fetch variants for asyncpg) to emit
``SqlEvent`` for every statement. Targets SQLAlchemy 2.x sync connections
and asyncpg async connections.

Patched lazily after the library is first imported — safe to import even when
the target libraries are not installed.
"""

import time
from typing import Any

from pai.events import SqlEvent
from pai.writer import EventWriter

__all__ = [
    "SqlCollector",
    "extract_sql_operation",
    "patch_asyncpg",
    "patch_asyncpg_execute",
    "patch_asyncpg_fetch",
    "patch_asyncpg_fetchrow",
    "patch_asyncpg_fetchval",
    "patch_sqlalchemy",
]


def extract_sql_operation(query: str) -> str:
    """Return the first word of a SQL query as the operation name, uppercased."""
    stripped = query.strip()
    if not stripped:
        return "UNKNOWN"
    return stripped.split()[0].upper()


class SqlCollector:
    """Holds the writer; provides patch methods for each supported SQL library."""

    def __init__(self, writer: EventWriter) -> None:
        self.writer = writer

    def record(self, query: str, duration_ms: int) -> None:
        self.writer.write(
            SqlEvent(
                operation=extract_sql_operation(query),
                query=query,
                duration_ms=duration_ms,
            )
        )


def patch_sqlalchemy(collector: SqlCollector, connection_cls: Any) -> None:
    """Wrap ``connection_cls.execute`` to emit a ``SqlEvent`` per statement."""
    original = connection_cls.execute

    def patched(self: Any, statement: Any, *args: Any, **kwargs: Any) -> Any:
        query = str(statement)
        start = time.monotonic()
        result = original(self, statement, *args, **kwargs)
        collector.record(query, int((time.monotonic() - start) * 1000))
        return result

    connection_cls.execute = patched


def patch_asyncpg(collector: SqlCollector, connection_cls: Any) -> None:
    """Wrap all async query methods on ``connection_cls`` to emit ``SqlEvent``."""
    patch_asyncpg_execute(collector, connection_cls)
    patch_asyncpg_fetch(collector, connection_cls)
    patch_asyncpg_fetchrow(collector, connection_cls)
    patch_asyncpg_fetchval(collector, connection_cls)


def patch_asyncpg_execute(collector: SqlCollector, connection_cls: Any) -> None:
    """Wrap ``connection_cls.execute``."""
    try:
        original = connection_cls.execute
    except AttributeError:
        return

    async def patched(self: Any, query: str, *args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        result = await original(self, query, *args, **kwargs)
        collector.record(query, int((time.monotonic() - start) * 1000))
        return result

    connection_cls.execute = patched


def patch_asyncpg_fetch(collector: SqlCollector, connection_cls: Any) -> None:
    """Wrap ``connection_cls.fetch``."""
    try:
        original = connection_cls.fetch
    except AttributeError:
        return

    async def patched(self: Any, query: str, *args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        result = await original(self, query, *args, **kwargs)
        collector.record(query, int((time.monotonic() - start) * 1000))
        return result

    connection_cls.fetch = patched


def patch_asyncpg_fetchrow(collector: SqlCollector, connection_cls: Any) -> None:
    """Wrap ``connection_cls.fetchrow``."""
    try:
        original = connection_cls.fetchrow
    except AttributeError:
        return

    async def patched(self: Any, query: str, *args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        result = await original(self, query, *args, **kwargs)
        collector.record(query, int((time.monotonic() - start) * 1000))
        return result

    connection_cls.fetchrow = patched


def patch_asyncpg_fetchval(collector: SqlCollector, connection_cls: Any) -> None:
    """Wrap ``connection_cls.fetchval``."""
    try:
        original = connection_cls.fetchval
    except AttributeError:
        return

    async def patched(self: Any, query: str, *args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        result = await original(self, query, *args, **kwargs)
        collector.record(query, int((time.monotonic() - start) * 1000))
        return result

    connection_cls.fetchval = patched
