"""Collector for runtime module imports via the ``builtins.__import__`` hook.

Wraps ``builtins.__import__`` with an ``ImportCollector`` instance whose
``patched_import`` method records every (caller, module) edge once, then delegates
to the original import function. Transitive imports (modules loaded while loading
another) are captured automatically because ``builtins.__import__`` is replaced
globally.
"""

import builtins
import types
from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast

from pai.events import ImportEvent
from pai.writer import EventWriter

__all__ = ["ImportCollector", "install", "resolve_module_name"]

ImportCallable = Callable[
    [
        str,
        Mapping | None,
        Mapping | None,
        Sequence[str] | None,
        int,
    ],
    types.ModuleType,
]


def resolve_module_name(name: str, package: str, level: int) -> str:
    """Convert a potentially relative import name to its absolute dotted form."""
    if level == 0:
        return name

    parts = package.split(".")
    if level > 1:
        trim = level - 1
        parts = parts[:-trim] if len(parts) >= trim else []

    if name:
        return ".".join(parts + [name])
    return ".".join(parts)


class ImportCollector:
    """Records import edges via a patched ``__import__`` function."""

    def __init__(self, writer: EventWriter, original_import: ImportCallable) -> None:
        self.writer = writer
        self.original_import = original_import
        self.seen: set[tuple[str, str]] = set()

    def patched_import(
        self,
        name: str,
        globals: Mapping | None = None,
        locals: Mapping | None = None,
        fromlist: Sequence[str] | None = None,
        level: int = 0,
    ) -> types.ModuleType:
        result = self.original_import(name, globals, locals, fromlist, level)

        caller = "__unknown__"
        if globals:
            caller_name = globals.get("__name__")
            if isinstance(caller_name, str):
                caller = caller_name

        package = ""
        if globals:
            pkg = globals.get("__package__")
            if isinstance(pkg, str):
                package = pkg

        absolute_name = resolve_module_name(name, package, level)

        if absolute_name:
            edge = (caller, absolute_name)
            if edge not in self.seen:
                self.seen.add(edge)
                self.writer.write(ImportEvent(module=caller, imported=absolute_name))

        return result


def install(writer: EventWriter) -> None:
    """Replace ``builtins.__import__`` with an ``ImportCollector`` hook."""
    original_import = cast(ImportCallable, builtins.__import__)
    collector = ImportCollector(
        writer=writer,
        original_import=original_import,
    )
    patched_import = cast(Any, collector.patched_import)
    builtins.__import__ = patched_import
