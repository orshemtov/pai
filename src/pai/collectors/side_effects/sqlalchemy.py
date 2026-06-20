"""SQLAlchemy side-effect collector."""

import time
from typing import Any

from pai.events import SqlalchemyEvent
from pai.writer import EventWriter

__all__ = ["SqlalchemyCollector", "extract_sql_operation", "patch_sqlalchemy"]


def extract_sql_operation(query: str) -> str:
    """Return the first word of a SQL query as the operation name."""
    stripped = query.strip()
    if not stripped:
        return "UNKNOWN"
    return stripped.split()[0].upper()


class SqlalchemyCollector:
    """Records SQL statements executed through SQLAlchemy."""

    def __init__(self, writer: EventWriter) -> None:
        self.writer = writer

    def record(self, query: str, duration_ms: int) -> None:
        event = SqlalchemyEvent(
            operation=extract_sql_operation(query),
            query=query,
            duration_ms=duration_ms,
        )
        self.writer.write(event)


def patch_sqlalchemy(collector: SqlalchemyCollector, connection_cls: Any) -> None:
    """Wrap ``Connection.execute``."""
    original = connection_cls.execute

    def patched(self: Any, statement: Any, *args: Any, **kwargs: Any) -> Any:
        query = str(statement)
        start = time.monotonic()
        result = original(self, statement, *args, **kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)
        collector.record(query, duration_ms)
        return result

    connection_cls.execute = patched
