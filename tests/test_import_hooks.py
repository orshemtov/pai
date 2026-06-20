"""Tests for ImportCollector post-import hook registration."""

import builtins
import json
from pathlib import Path

from pai.collectors.imports import ImportCollector
from pai.writer import EventWriter


def read_events(run_dir: Path) -> list[dict]:
    result: list[dict] = []
    events_path = run_dir / "events.jsonl"
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            result.append(json.loads(line))
    return result


def test_register_hook_fires_on_module_import(tmp_path: Path) -> None:
    fired: list[str] = []

    with EventWriter(tmp_path) as writer:
        collector = ImportCollector(writer=writer, original_import=builtins.__import__)
        collector.register_hook("colorsys", lambda mod: fired.append(mod.__name__))

        old = builtins.__import__
        builtins.__import__ = collector.patched_import  # type: ignore
        try:
            import colorsys  # noqa: F401,PLC0415
        finally:
            builtins.__import__ = old

    assert "colorsys" in fired


def test_register_hook_fires_only_once(tmp_path: Path) -> None:
    fired: list[str] = []

    with EventWriter(tmp_path) as writer:
        collector = ImportCollector(writer=writer, original_import=builtins.__import__)
        collector.register_hook("colorsys", lambda mod: fired.append(mod.__name__))

        old = builtins.__import__
        builtins.__import__ = collector.patched_import  # type: ignore
        try:
            import colorsys  # noqa: F401,I001,PLC0415
            import colorsys  # noqa: F401,F811,PLC0415
        finally:
            builtins.__import__ = old

    assert len(fired) == 1


def test_register_hook_not_fired_for_other_modules(tmp_path: Path) -> None:
    fired: list[str] = []

    with EventWriter(tmp_path) as writer:
        collector = ImportCollector(writer=writer, original_import=builtins.__import__)
        collector.register_hook("colorsys", lambda mod: fired.append(mod.__name__))

        old = builtins.__import__
        builtins.__import__ = collector.patched_import  # type: ignore
        try:
            import textwrap  # noqa: F401,PLC0415
        finally:
            builtins.__import__ = old

    assert len(fired) == 0
