"""Collector for uncaught exceptions.

Installs ``sys.excepthook`` and ``threading.excepthook`` via ``ExceptionCollector``,
which holds the writer and original hooks as injected dependencies.

Only the *shape* of local variables is recorded (type names and dict keys) — never
raw values — to avoid leaking user data.
"""

import sys
import threading
from collections.abc import Callable
from types import TracebackType

from pai.events import ExceptionEvent, LocalSchema
from pai.writer import EventWriter

ExceptHookCallable = Callable[[type[BaseException], BaseException, TracebackType | None], None]
ThreadExceptHookCallable = Callable[[threading.ExceptHookArgs], None]

__all__ = [
    "ExceptionCollector",
    "build_exception_event",
    "deepest_traceback",
    "install",
    "local_schema",
]


def deepest_traceback(tb: TracebackType) -> TracebackType:
    deepest = tb
    while deepest.tb_next is not None:
        deepest = deepest.tb_next
    return deepest


def local_schema(value) -> LocalSchema:
    schema: LocalSchema = {"type": type(value).__name__}

    if isinstance(value, dict):
        keys: list[str] = []
        for key in value:
            keys.append(str(key))
        schema["keys"] = keys

    return schema


def build_exception_event(
    exc_type: type[BaseException],
    exc: BaseException,
    tb: TracebackType,
) -> ExceptionEvent:
    """Build a structured event from an exception and its traceback."""
    deepest = deepest_traceback(tb)
    frame = deepest.tb_frame
    code = frame.f_code

    module = frame.f_globals.get("__name__", "?")
    symbol = f"{module}.{code.co_qualname}"

    locals_schema: dict[str, LocalSchema] = {}
    for name, value in frame.f_locals.items():
        locals_schema[name] = local_schema(value)

    return ExceptionEvent(
        symbol=symbol,
        file=code.co_filename,
        line=deepest.tb_lineno,
        exception_type=exc_type.__name__,
        message=str(exc),
        locals_schema=locals_schema,
    )


class ExceptionCollector:
    """Holds injected dependencies and exposes hook callables for sys.excepthook."""

    def __init__(
        self,
        writer: EventWriter,
        original_excepthook: ExceptHookCallable,
        original_thread_hook: ThreadExceptHookCallable,
    ) -> None:
        self.writer = writer
        self.original_excepthook = original_excepthook
        self.original_thread_hook = original_thread_hook

    def exception_hook(
        self,
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        if tb is not None:
            self.writer.write(build_exception_event(exc_type, exc, tb))
        self.original_excepthook(exc_type, exc, tb)

    def thread_exception_hook(self, args: threading.ExceptHookArgs) -> None:
        tb = args.exc_traceback
        if args.exc_type is not None and args.exc_value is not None and tb is not None:
            self.writer.write(build_exception_event(args.exc_type, args.exc_value, tb))
        self.original_thread_hook(args)


def install(writer: EventWriter) -> None:
    """Wire an ``ExceptionCollector`` into ``sys.excepthook`` and ``threading.excepthook``."""
    collector = ExceptionCollector(
        writer=writer,
        original_excepthook=sys.excepthook,
        original_thread_hook=threading.excepthook,  # type: ignore
    )
    sys.excepthook = collector.exception_hook
    threading.excepthook = collector.thread_exception_hook
